import http
import logging
from typing import List, Optional, Union

from bson import ObjectId
from bson.errors import InvalidId
from fastapi import HTTPException

from app.helpers.events import EventType
from app.helpers.pfp import extract_contract_and_token_from_string, upload_pfp_url_and_update_profile
from app.helpers.queue_utils import queue_bg_task, queue_bg_tasks
from app.helpers.w3 import checksum_address, get_nft, get_nft_image_url, verify_token_ownership
from app.models.base import APIDocument
from app.models.channel import ChannelReadState
from app.models.report import UserReport
from app.models.server import ServerMember
from app.models.user import User, UserBlock, UserPreferences
from app.schemas.preferences import UserPreferencesUpdateSchema
from app.schemas.reports import UserReportCreateSchema
from app.schemas.servers import ServerMemberUpdateSchema
from app.schemas.users import UserBlockCreateSchema, UserCreateSchema, UserUpdateSchema
from app.services.apps import delete_user_apps
from app.services.channels import remove_user_channel_membership
from app.services.crud import create_item, delete_item, delete_items, get_item, get_items, update_item
from app.services.events import broadcast_event
from app.services.stars import delete_user_stars
from app.services.websockets import broadcast_server_event

logger = logging.getLogger(__name__)


async def create_user(user_model: UserCreateSchema) -> User:
    user_model.wallet_address = checksum_address(user_model.wallet_address)
    return await create_item(item=user_model, result_obj=User, user_field=None)


async def get_user_by_wallet_address(wallet_address: str) -> Union[User, APIDocument]:
    return await get_item(filters={"wallet_address": wallet_address}, result_obj=User)


async def get_user_by_signer(signer: str) -> Union[User, APIDocument]:
    return await get_item(filters={"signers": signer}, result_obj=User)


async def get_user_by_id(user_id) -> Union[User, APIDocument]:
    return await get_item(filters={"_id": ObjectId(user_id)}, result_obj=User)


async def get_user_profile_by_server_id(server_id: str, current_user: User) -> Union[ServerMember, APIDocument]:
    profile = await get_item(
        filters={"server": ObjectId(server_id), "user": current_user.pk},
        result_obj=ServerMember,
    )

    if not profile:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)

    return profile


async def set_user_profile_picture(data: dict, current_user: User, profile: User) -> dict:
    pfp_input_string = data.get("pfp", "")
    if not pfp_input_string:
        return data

    pfp_data = {"input": pfp_input_string}

    contract_address, token_id = await extract_contract_and_token_from_string(pfp_input_string)
    if contract_address and token_id:
        owns_nft = await verify_token_ownership(
            contract_address=contract_address,
            token_id=token_id,
            wallet_address=current_user.wallet_address,
        )
        if owns_nft:
            logger.debug(f"{current_user.id} owns {contract_address}/{token_id}")
            token = await get_nft(contract_address=contract_address, token_id=token_id)
            image_url = await get_nft_image_url(token)
            logger.debug(f"{contract_address}/{token_id} image: {image_url}")

            pfp_data.update(
                {
                    "contract": contract_address,
                    "token_id": token_id,
                    "verified": True,
                    "input_image_url": image_url,
                    "token": token,
                }
            )
        else:
            logger.debug(f"{current_user.id} does not own {contract_address}/{token_id}")
            del [data["pfp"]]
            return data
    else:
        image_url = pfp_input_string
        if not pfp_input_string.startswith("http"):
            del [data["pfp"]]
            return data

        pfp_data["verified"] = False
        pfp_data["input_image_url"] = image_url

    if image_url.startswith("http"):
        metadata = {"user": str(current_user.pk), "profile": str(profile.pk)}
        await queue_bg_task(upload_pfp_url_and_update_profile, pfp_input_string, image_url, profile, metadata)
    else:
        logger.warning("image found is not a URL, ignoring upload to cloudflare for now")

    data["pfp"] = pfp_data
    return data


async def update_user_profile(
    server_id: Optional[str], update_data: Union[UserUpdateSchema, ServerMemberUpdateSchema], current_user: User
) -> Union[ServerMember, User]:
    data = update_data.dict(exclude_unset=True)

    if server_id:
        profile = await get_item(
            filters={"server": ObjectId(server_id), "user": current_user.pk},
            result_obj=ServerMember,
        )

        if not profile:
            raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)
    else:
        profile = current_user

    if "pfp" in data:
        if data["pfp"] != "":
            data = await set_user_profile_picture(data, current_user=current_user, profile=profile)
        else:
            data["pfp"] = None

    updated_item = await update_item(item=profile, data=data)

    if data:
        if server_id:
            await queue_bg_task(
                broadcast_server_event,
                server_id,
                str(current_user.id),
                EventType.SERVER_PROFILE_UPDATE,
                {**data, "user": str(current_user.id), "member": str(profile.id)},
            )
        else:
            await queue_bg_task(
                broadcast_event,
                EventType.USER_PROFILE_UPDATE,
                {**data, "user": current_user.dump()},
            )

    return updated_item


async def get_user_read_states(current_user: User):
    return await get_items(filters={"user": current_user.pk}, result_obj=ChannelReadState, limit=None)


async def delete_user_read_states(current_user: User):
    await delete_items(filters={"user": current_user.pk}, result_obj=ChannelReadState)


async def get_users_info(data: dict):
    user_ids: List[str] = data.get("user_ids", [])
    user_obj_ids = []
    for user_id in user_ids:
        try:
            user_obj_ids.append(ObjectId(user_id))
        except InvalidId:
            pass

    return await get_items(filters={"_id": {"$in": user_obj_ids}}, result_obj=User)


async def get_user_preferences(current_user: User):
    return await get_item(filters={"user": current_user.pk}, result_obj=UserPreferences)


async def update_user_preferences(update_data: UserPreferencesUpdateSchema, current_user: User) -> UserPreferences:
    current_prefs = await get_user_preferences(current_user)

    if not current_prefs:
        return await create_item(item=update_data, result_obj=UserPreferences, current_user=current_user)

    data = update_data.dict(exclude_unset=True)
    return await update_item(item=current_prefs, data=data)


async def delete_user_preferences(current_user: User):
    prefs = await get_user_preferences(current_user)
    if prefs:
        await delete_item(item=prefs)


async def report_user(report_model: UserReportCreateSchema, current_user: User):
    user_id = report_model.user
    if user_id == str(current_user.pk):
        raise HTTPException(status_code=http.HTTPStatus.BAD_REQUEST, detail="One cannot report themselves")

    is_reported = await get_item(filters={"user": ObjectId(user_id), "author": current_user.pk}, result_obj=UserReport)
    if is_reported:
        raise HTTPException(status_code=http.HTTPStatus.BAD_REQUEST, detail="User has already been reported")

    return await create_item(report_model, result_obj=UserReport, user_field="author", current_user=current_user)


async def block_user(block_model: UserBlockCreateSchema, current_user: User):
    user_id = block_model.user

    if user_id == str(current_user.pk):
        raise HTTPException(status_code=http.HTTPStatus.BAD_REQUEST, detail="One cannot block themselves")

    is_blocked = await get_item(filters={"user": ObjectId(user_id), "author": current_user.pk}, result_obj=UserBlock)
    if is_blocked:
        raise HTTPException(status_code=http.HTTPStatus.BAD_REQUEST, detail="User has already been blocked")

    await create_item(block_model, result_obj=UserBlock, user_field="author", current_user=current_user)


async def unblock_user(user_id: str, current_user: User):
    block_item = await get_item(filters={"user": ObjectId(user_id), "author": current_user.pk}, result_obj=UserBlock)
    if not block_item:
        raise HTTPException(status_code=http.HTTPStatus.NOT_FOUND)

    await delete_item(block_item)


async def get_blocked_users(current_user: User):
    return await get_items(filters={"author": current_user.pk}, result_obj=UserBlock, limit=None)


async def delete_all_blocked_users(current_user: User):
    await delete_items(filters={"author": current_user.pk}, result_obj=UserBlock)


async def delete_user(current_user: User):
    await update_item(
        current_user,
        data={
            "deleted": True,
            "pfp": None,
            "display_name": None,
            "ens_domain": None,
            "description": None,
            "online_channels": [],
            "push_tokens": [],
            "status": "offline",
        },
    )

    logger.info("Deleted user %s. Queueing other data for deletion", current_user.pk)

    bg_tasks = [
        (remove_user_channel_membership, (current_user,)),
        (delete_user_read_states, (current_user,)),
        (delete_user_preferences, (current_user,)),
        (delete_all_blocked_users, (current_user,)),
        (delete_user_apps, (current_user,)),
        (delete_user_stars, (current_user,)),
    ]

    await queue_bg_tasks(bg_tasks)  # type: ignore[arg-type]
