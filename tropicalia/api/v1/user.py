from fastapi import APIRouter, HTTPException

router = APIRouter()

# @router.post(
#     "/register",
#     summary="Sing-up authentication endpoint",
#     tags=["auth"],
#     response_model=UserInDB,
#     response_description="User model from database",
# )
# async def register_to_system(user: UserCreateRequest, db: AsyncIOMotorClient = Depends(get_connection)):
#     user_by_email = await get_user_by_email(db, user.email)
#     if user_by_email:
#         raise HTTPException(
#             status_code=HTTP_409_CONFLICT,
#             detail="Email already in use",
#         )
#     user_by_username = await get_user_by_username(db, user.username)
#     if user_by_username:
#         raise HTTPException(
#             status_code=HTTP_409_CONFLICT,
#             detail="User already in use",
#         )
    
#     await send_mail([user.email]) 
#     #await send_mail(["pedgm@uma.es"])   
    
#     user_in_db = await register_user(db, user) # User is disabled until email confirmation
#     return user_in_db