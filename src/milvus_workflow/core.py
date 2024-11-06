import logging
from dataclasses import dataclass

from pymilvus import MilvusClient

logger = logging.getLogger(__name__)


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


def project_create_resources(
    client: MilvusClient,
    resource_names: ProjectResourceNaming,
    recreate_resources: bool = False,
):
    rn = resource_names

    # Check the status of each resource
    database_exists = rn.database_name in client.list_databases()
    user_exists = rn.user_name in client.list_users()
    role_exists = rn.role_name in client.list_roles()

    # Log initial status
    logger.info(f"\nProject resources for '{rn.project_name}':")
    logger.info("─" * 50)
    logger.info(format_resource_status(rn.database_name, database_exists, "database"))
    logger.info(format_resource_status(rn.user_name, user_exists, "user"))
    logger.info(format_resource_status(rn.role_name, role_exists, "role"))

    # Handle recreation if needed
    if recreate_resources and (database_exists or user_exists or role_exists):
        logger.info("\nRecreating existing resources:")
        if database_exists:
            client.drop_database(rn.database_name)
            logger.info("  • Dropped database")
            database_exists = False
        if user_exists:
            client.drop_user(rn.user_name)
            logger.info("  • Dropped user")
            user_exists = False
        if role_exists:
            client.drop_role(rn.role_name)
            logger.info("  • Dropped role")
            role_exists = False

    # Create resources
    logger.info("\nCreating resources:")
    if not database_exists:
        client.create_database(rn.database_name)
        logger.info("  • Created database")

    if not user_exists:
        client.create_user(user_name=rn.user_name, password=rn.user_password)
        logger.info("  • Created user")

    if not role_exists:
        client.create_role(rn.role_name)
        logger.info("  • Created role")

        # Grant privileges
        collection_privileges = [
            "CreateIndex",
            "Load",
            "Insert",
            "Delete",
            "Search",
            "Query",
            "Flush",
        ]

        logger.info("\nGranting privileges:")
        for privilege in collection_privileges:
            client.grant_privilege(
                role_name=rn.role_name,
                object_type="Collection",
                object_name="*",
                privilege=privilege,
            )
            logger.info(f"  • {privilege} on Collection")

        client.grant_role(rn.user_name, rn.role_name)
        logger.info(f"\nAssigned role '{rn.role_name}' to user '{rn.user_name}'")


def format_resource_status(
    name: str, exists: bool, resource_type: str = "resource"
) -> str:
    """Format a resource status line with consistent symbols and indentation."""
    status_symbol = "✓" if exists else "×"
    status_color = "32" if exists else "31"  # 32=green, 31=red
    return f"  \033[{status_color}m{status_symbol}\033[0m {resource_type}: {name}"


def project_describe_resources(
    client: MilvusClient, project_name: str, user_name: None | str = None
):
    """List the resources and collections in a project and check user privileges."""
    database_name = f"db_{project_name}"
    role_name = f"role_{project_name}"

    database_exists = database_name in client.list_databases()
    role_exists = role_name in client.list_roles()

    users = client.list_users()

    logger.info(f"\nProject resources for '{project_name}':")
    logger.info("─" * 50)
    logger.info(format_resource_status(database_name, database_exists, "database"))
    logger.info(format_resource_status(role_name, role_exists, "role"))

    if not database_exists:
        logger.info("\nℹ️  No additional information (database does not exist)")
        return

    collections: list[str] = client.list_collections()
    if collections:
        logger.info("\nCollections:")
        for coll in collections:
            logger.info(f"  • {coll}")
    else:
        logger.info("\nNo collections found in database")

    if user_name or len(users) > 0:
        users_to_check = [user_name] if user_name else users
        logger.info("\nUser privileges:")
        for user in users_to_check:
            logger.info(f"\n  User: {user}")
            for role in client.list_roles():
                privileges: list[dict[str, str]] = client.describe_role(role_name=role)[
                    "privileges"
                ]
                if privileges:
                    logger.info(f"    Role '{role}':")
                    for p in privileges:
                        logger.info(f"      • {p['privilege']} on {p['object_type']}")


def project_drop_resources(
    client: MilvusClient,
    project_name: str,
    database_name: None | str = None,
    role_name: None | str = None,
    user_name: None | str = None,
):
    """Drop all resources associated with a project."""
    database_name = database_name or f"db_{project_name}"
    role_name = role_name or f"role_{project_name}"
    user_name = user_name or f"user_{project_name}"

    database_exists = database_name in client.list_databases()
    user_exists = user_name in client.list_users()
    role_exists = role_name in client.list_roles()

    # Log initial status
    logger.info(f"\nProject resources for '{project_name}':")
    logger.info("─" * 50)
    logger.info(format_resource_status(database_name, database_exists, "database"))
    logger.info(format_resource_status(user_name, user_exists, "user"))
    logger.info(format_resource_status(role_name, role_exists, "role"))

    if not any([database_exists, user_exists, role_exists]):
        logger.info("\nℹ️  No resources to drop")
        return

    logger.info("\nDropping resources:")
    if database_exists:
        client.drop_database(database_name)
        logger.info(f"  • Dropped database '{database_name}'")

    if user_exists:
        client.drop_user(user_name)
        logger.info(f"  • Dropped user '{user_name}'")

    if role_exists:
        for priv in client.describe_role(role_name)["privileges"]:  # type: ignore
            client.revoke_privilege(**priv)
        client.drop_role(role_name)
        logger.info(f"  • Dropped role '{role_name}'")


def database_list_all(client: MilvusClient):
    """List all databases and their details."""
    databases = client.list_databases()
    logger.info(f"Found {len(databases)} databases:")
    for db in databases:
        logger.info(f"\nDatabase: {db}")
        try:
            collections = client.list_collections()
            logger.info(f"  Collections: {collections}")
        except Exception as _:
            logger.info("  Collections: Unable to list (insufficient privileges)")
