from pydantic import BaseModel, ConfigDict


class BaseModelSchema(BaseModel):
    """Base Pydantic model for request schemas."""
    
    model_config = ConfigDict(
        from_attributes=True,
        str_strip_whitespace=True,
        validate_assignment=True,
    )


class BaseCreateSchema(BaseModelSchema):
    """Base schema for create operations."""
    pass


class BaseUpdateSchema(BaseModelSchema):
    """Base schema for update operations - all fields optional."""
    pass


class BaseResponseSchema(BaseModelSchema):
    """Base schema for API responses."""
    pass
