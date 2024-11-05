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
    recreate_resources: bool = False,
):
    rn = resource_names

    # Check the status of each resource
    database_exists = client.database_exists(rn.database_name)
    user_exists = client.user_exists(rn.user_name)
    role_exists = client.role_exists(rn.role_name)

    # Print the status of each resource
    print(f"Database {rn.database_name} exists: {'✅' if database_exists else '❌'}")
    print(f"User {rn.user_name} exists: {'✅' if user_exists else '❌'}")
    print(f"Role {rn.role_name} exists: {'✅' if role_exists else '❌'}")

    # 0. Drop existing resources if recreate=True
    if recreate_resources:
        if database_exists:
            client.drop_database(rn.database_name)
        if user_exists:
            client.drop_user(rn.user_name)
        if role_exists:
            client.drop_role(rn.role_name)

    # 1. Create project database
    if database_exists:
        raise ResourceExistsError(f"Database {rn.database_name} already exists.")
    else:
        client.create_database(rn.database_name)

    # 2. Create project user
    if user_exists:
        raise ResourceExistsError(f"User {rn.user_name} already exists.")
    else:
        client.create_user(user_name=rn.user_name, password=rn.user_password)

    # 3. Create project role in the database
    if role_exists:
        raise ResourceExistsError(f"Role {rn.role_name} already exists.")
    else:
        client.create_role(rn.role_name)

        # Grant collection-level privileges for typical vector DB operations
        collection_privileges = [
            "CreateIndex",  # Create vector indexes
            "Load",  # Load collections into memory
            "Insert",  # Add new vectors
            "Delete",  # Remove vectors
            "Search",  # Vector similarity search
            "Query",  # Attribute filtering
            "Flush",  # Ensure data persistence
        ]

        for privilege in collection_privileges:
            client.grant_privilege(rn.role_name, rn.database_name, "*", privilege)
            print(f"Granted {privilege} privilege to role {rn.role_name}")

        # Assign role to user
        client.add_user_to_role(rn.user_name, rn.role_name)
        print(f"Assigned role {rn.role_name} to user {rn.user_name}")


def list_project_resources(
    client: MilvusClient, project_name: str, user_name: str = None
):
    """List the resources and collections in a project and check user privileges."""
    database_name = f"db_{project_name}"
    role_name = f"role_{project_name}"
    default_user_name = f"user_{project_name}"

    database_exists = client.database_exists(database_name)
    user_exists = (
        client.user_exists(user_name)
        if user_name
        else client.user_exists(default_user_name)
    )
    role_exists = client.role_exists(role_name)

    print(f"Database {database_name} exists: {'✅' if database_exists else '❌'}")
    print(
        f"User {user_name or default_user_name} exists: {'✅' if user_exists else '❌'}"
    )
    print(f"Role {role_name} exists: {'✅' if role_exists else '❌'}")

    if database_exists:
        collections = client.list_collections(database_name)
        print(f"Collections in {database_name}: {collections}")

        users_to_check = [user_name] if user_name else client.list_users(database_name)
        for user in users_to_check:
            print(f"Checking privileges for user {user}:")
            for collection in collections:
                privileges = client.get_privileges(user, database_name, collection)
                print(f"  Collection {collection}: {privileges}")
    else:
        print(f"No collections found as database {database_name} does not exist.")

    # Hide the password in the output
    print("User password: (hidden)")
