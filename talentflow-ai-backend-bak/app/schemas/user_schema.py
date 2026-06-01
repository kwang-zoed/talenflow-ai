from pydantic import BaseModel,Field,EmailStr,ConfigDict
from typing import Optional,List
from datetime import datetime

# 基础共享属性
class UserBase(BaseModel):
    username: str = Field(..., min_length=2,max_length=50, description="用户名")
    email: EmailStr = Field(..., description="邮箱")
    role: int = Field( default=0, description="角色,0:普通用户,1:管理员,2:hr")

# 创建用户
class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=20, description="密码")

# 更新用户
class UserUpdate(BaseModel):
    username: Optional[str] = Field(None, min_length=2, max_length=50)
    email: Optional[EmailStr] = Field(None)
    role: Optional[int] = Field(None)
    full_name: Optional[str] = Field(None)
    is_active: Optional[bool] = Field(None)


# 用户读取模型 - 用于列表和详情
class UserRead(BaseModel):
    id: int
    username: str
    email: Optional[str]
    full_name: Optional[str]
    role: int
    is_active: bool
    created_at: Optional[datetime]
    
    model_config = ConfigDict(from_attributes=True)


# 带分页的用户列表响应
class UserListResponse(BaseModel):
    total: int
    items: List[UserRead]


class LoginResponse(BaseModel):
    access_token: str
    token_type: str
    user: dict
