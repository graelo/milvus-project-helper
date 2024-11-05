from dataclasses import dataclass

from pymilvus import MilvusClient


@dataclass
class ProjectResourceNaming:
    project_name: str
    database_name: str
    role_name: str
    user_name: str
    user_password: str


class PasswordStrengthError(Exception):
    pass


class ResourceExistsError(Exception):
    pass


def check_password_strength(password: str):
    """Check if the password is strong enough according to Milvus requirements."""
    if len(password) < 8:
        raise PasswordStrengthError("Password must be at least 8 characters long")
    if not any(c.isupper() for c in password):
        raise PasswordStrengthError(
            "Password must contain at least one uppercase letter"
        )
    if not any(c.islower() for c in password):
        raise PasswordStrengthError(
            "Password must contain at least one lowercase letter"
        )
    if not any(c.isdigit() for c in password):
        raise PasswordStrengthError("Password must contain at least one digit")
    if not any(c in "!@#$%^&*()-+" for c in password):
        raise PasswordStrengthError(
            "Password must contain at least one special character"
        )


def setup_project_resources(
    client: MilvusClient,
    resource_names: ProjectResourceNaming,
    recreate: bool = False,
    skip_if_exists: bool = False,
):
    rn = resource_names

    # 0. Drop existing resources if recreate=True
    if recreate:
        client.drop_database(rn.database_name)
        client.drop_user(rn.user_name)
        client.drop_role(rn.role_name)

    # 1. Create project database
    if client.database_exists(rn.database_name):
        if skip_if_exists:
            print(f"Database {rn.database_name} already exists, skipping.")

        else:
            raise ResourceExistsError(f"Database {rn.database_name} already exists.")
    else:
        client.create_database(rn.database_name)

    # 2. Create project user
    if client.user_exists(rn.user_name):
        if skip_if_exists:
            print(f"User {rn.user_name} already exists, skipping.")
        else:
            raise ResourceExistsError(f"User {rn.user_name} already exists.")
    else:
        client.create_user(user_name=rn.user_name, password=rn.user_password)

    # 3. Create project role in the database
    if client.role_exists(rn.role_name):
        if skip_if_exists:
            print(f"Role {rn.role_name} already exists, skipping.")
        else:
            raise ResourceExistsError(f"Role {rn.role_name} already exists.")
    else:
        client.create_role(rn.role_name)

    # 4. Grant database-specific privileges
    if not client.has_privilege(
        role_name=rn.role_name,
        object_type="Collection",
        object_name="*",
        privilege="CreateCollection",
        db_name=rn.database_name,
    ):
        client.grant_privilege(
            role_name=rn.role_name,
            object_type="Collection",
            object_name="*",
            privilege="CreateCollection",
            db_name=rn.database_name,
        )
    else:
        print(f"Privilege already granted to role {rn.role_name}.")

    # 5. Bind role to user
    if not client.has_role(user_name=rn.user_name, role_name=rn.role_name):
        client.grant_role(user_name=rn.user_name, role_name=rn.role_name)
    else:
        print(f"Role {rn.role_name} already granted to user {rn.user_name}.")
