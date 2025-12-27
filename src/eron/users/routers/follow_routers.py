from fastapi import APIRouter, Depends, HTTPException, status
from bson import ObjectId
from beanie import PydanticObjectId
from eron.users.utils.get_current_user import get_current_user
from eron.users.models.user_models import UserModel
from typing import List

router = APIRouter(
    prefix="/social",
    tags=["Social & Connections"]
)


@router.post("/follow/{target_id}")
async def follow_user(target_id: str, current_user: UserModel = Depends(get_current_user)):
    # target_id কে PydanticObjectId তে রূপান্তর
    try:
        target_oid = PydanticObjectId(target_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid User ID format")

    if target_id == str(current_user.id):
        raise HTTPException(status_code=400, detail="You cannot follow yourself")

    target_user = await UserModel.get(target_oid)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    # Beanie Link চেক করার সঠিক উপায়
    is_already_following = any(link.ref.id == target_oid for link in current_user.following)

    if is_already_following:
        return {"message": "Already following this user"}

    current_user.following.append(target_user)
    current_user.following_count += 1
    target_user.followers_count += 1

    await current_user.save()
    await target_user.save()

    return {"message": "Followed successfully"}


@router.post("/unfollow/{target_id}")
async def unfollow_user(target_id: str, current_user: UserModel = Depends(get_current_user)):
    try:
        target_oid = PydanticObjectId(target_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid User ID format")

    target_user_in_list = None
    for link in current_user.following:
        if link.ref.id == target_oid:
            target_user_in_list = link
            break

    if not target_user_in_list:
        raise HTTPException(status_code=400, detail="You are not following this user")

    target_user = await UserModel.get(target_oid)
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found")

    current_user.following.remove(target_user_in_list)
    current_user.following_count = max(0, current_user.following_count - 1)
    target_user.followers_count = max(0, target_user.followers_count - 1)

    await current_user.save()
    await target_user.save()

    return {"status": "success", "message": f"Unfollowed {target_user.first_name}"}


@router.get("/me/following-list")
async def get_my_following(current_user: UserModel = Depends(get_current_user)):
    # fetch_links=True সরাসরি রিলেটেড ডাটা নিয়ে আসে
    user = await UserModel.find_one(UserModel.id == current_user.id, fetch_links=True)
    return user.following


@router.get("/active-priority-list")
async def get_active_priority_list(current_user: UserModel = Depends(get_current_user)):
    """
    আপনার মূল রিকোয়ারমেন্ট: B ইউজারকে (ফলো করা ইউজার) সবার উপরে রেখে অনলাইন লিস্ট
    """
    # ১. অনলাইনে থাকা ইউজারদের আনা
    online_users = await UserModel.find(UserModel.is_online == True).to_list()

    # ২. কারেন্ট ইউজারের ফলোয়িং আইডিগুলোর একটি সেট তৈরি (দ্রুত সার্চের জন্য)
    following_ids = {str(link.ref.id) for link in current_user.following}

    # ৩. সর্টিং: B (যাকে ফলো করছেন) লিস্টের উপরে থাকবে
    online_users.sort(key=lambda u: str(u.id) in following_ids, reverse=True)

    return online_users


@router.get("/me/followers-list")
async def get_my_followers(current_user: UserModel = Depends(get_current_user)):
    """
    কারা আপনাকে ফলো করছে তাদের লিস্ট বের করা।
    লজিক: এমন ইউজারদের খুঁজে বের করো যাদের 'following' লিস্টে আপনার ID আছে।
    """
    followers = await UserModel.find(
        UserModel.following.id == current_user.id
    ).to_list()

    return followers


@router.get("/me/counts")
async def get_social_counts(current_user: UserModel = Depends(get_current_user)):
    """
    নিজের ফলোয়ার এবং ফলোয়িং সংখ্যা দেখার জন্য।
    """
    return {
        "follower_count": current_user.followers_count,
        "following_count": current_user.following_count
    }


# আপনি চাইলে নির্দিষ্ট কোনো ইউজারের আইডি দিয়েও তার কাউন্ট দেখতে পারেন
@router.get("/{user_id}/stats")
async def get_user_stats(user_id: str):
    try:
        user_oid = PydanticObjectId(user_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid User ID format")

    user = await UserModel.get(user_oid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "username": f"{user.first_name} {user.last_name}",
        "follower_count": user.followers_count,
        "following_count": user.following_count
    }