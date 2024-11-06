import logging
from typing_extensions import Annotated

import typer
from pymilvus import MilvusClient

from .core import (
    ProjectResourceNaming,
    check_password_strength,
    project_create_resources,
    project_drop_resources,
    PasswordStrengthError,
    ResourceExistsError,
    project_describe_resources,
    database_list_all,
)

logger = logging.getLogger(__name__)

app = typer.Typer(no_args_is_help=True)

project_app = typer.Typer()
database_app = typer.Typer()
app.add_typer(project_app, name="project")
app.add_typer(database_app, name="database")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",  # Simple format since this is a CLI tool
)


@project_app.command("create")
def project_create(
    uri: Annotated[
        str,
        typer.Option(
            envvar="MILVUS_URI",
            help="URI of the Milvus gRPC endpoint, e.g. 'http://root:Milvus@localhost:19530'. "
            "The user must be able to create databases, roles and users",
        ),
    ],
    dry_run: bool = typer.Option(
        True,
        help="Print the commands that would be executed without actually running them",
    ),
    force: bool = typer.Option(
        False,
        help="Recreate the project resources if they already exist",
    ),
    database_name: Annotated[
        None | str,
        typer.Option(
            help="Name of the database to use for the project "
            "(default: 'db_<project_name>')",
        ),
    ] = None,
    role_name: Annotated[
        None | str,
        typer.Option(
            help="Name of the role to use for the project "
            "(default: 'role_<project_name>')",
        ),
    ] = None,
    user_name: Annotated[
        None | str,
        typer.Option(
            help="Name of the user to use for the project "
            "(default: 'user_<project_name>')",
        ),
    ] = None,
    user_password: Annotated[
        None | str, typer.Option(help="Password for the new user")
    ] = None,
    project_name: Annotated[
        str, typer.Argument(help="New project name")
    ] = "new-project",
):
    logger.info(f"Setting up project `{project_name}`...")
    if not user_password:
        user_password = typer.prompt("Enter password for the new user", hide_input=True)
    assert user_password is not None and user_password != ""

    try:
        check_password_strength(user_password)
    except PasswordStrengthError as e:
        typer.echo("❌ " + str(e))  # Keep typer.echo for error messages
        raise typer.Exit(code=1)

    resource_names = ProjectResourceNaming(
        project_name=project_name,
        database_name=database_name or f"db_{project_name}",
        role_name=role_name or f"role_{project_name}",
        user_name=user_name or f"user_{project_name}",
        user_password=user_password,
    )

    for k, v in resource_names.__dict__.items():
        if k == "user_password":
            logger.info(f"  {k}: (hidden)")
        else:
            logger.info(f"  {k}: {v}")

    if dry_run:
        logger.info("Dry run: exiting without executing commands")
        return

    client = MilvusClient(uri=uri)

    try:
        project_create_resources(
            client,
            resource_names,
            recreate_resources=force,
        )
    except ResourceExistsError as e:
        typer.echo("❌ " + str(e))
        raise typer.Exit(code=1)


@project_app.command("describe")
def project_describe(
    uri: Annotated[
        str,
        typer.Option(
            envvar="MILVUS_URI",
            help="URI of the Milvus gRPC endpoint, e.g. 'http://root:Milvus@localhost:19530'. "
            "The user must be able to create databases, roles and users",
        ),
    ],
    project_name: Annotated[
        str, typer.Argument(help="Name of the project to list resources for")
    ],
    user_name: Annotated[
        None | str,
        typer.Option(
            help="Name of the user to check privileges for (default: check all users)"
        ),
    ] = None,
):
    logger.info(f"Listing resources for project `{project_name}`...")

    client = MilvusClient(uri=uri)

    project_describe_resources(client, project_name, user_name)


@project_app.command("drop")
def project_drop(
    uri: Annotated[
        str,
        typer.Option(
            envvar="MILVUS_URI",
            help="URI of the Milvus gRPC endpoint, e.g. 'http://root:Milvus@localhost:19530'. "
            "The user must be able to drop databases, roles and users",
        ),
    ],
    project_name: Annotated[str, typer.Argument(help="Name of the project to drop")],
    database_name: Annotated[
        None | str,
        typer.Option(
            help="Name of the database to drop (default: 'db_<project_name>')",
        ),
    ] = None,
    role_name: Annotated[
        None | str,
        typer.Option(
            help="Name of the role to drop (default: 'role_<project_name>')",
        ),
    ] = None,
    user_name: Annotated[
        None | str,
        typer.Option(
            help="Name of the user to drop (default: 'user_<project_name>')",
        ),
    ] = None,
    dry_run: bool = typer.Option(
        True,
        help="Print the resources that would be dropped without actually dropping them",
    ),
):
    logger.info(f"Dropping project `{project_name}`...")

    if dry_run:
        logger.info("Dry run: would drop these resources:")
        logger.info(f"  database: {database_name or f'db_{project_name}'}")
        logger.info(f"  role: {role_name or f'role_{project_name}'}")
        logger.info(f"  user: {user_name or f'user_{project_name}'}")
        return

    if not typer.confirm(
        "Are you sure you want to drop these resources?"
    ):  # Keep interactive prompts
        typer.echo("Operation cancelled")  # Keep user feedback
        raise typer.Exit(code=1)

    client = MilvusClient(uri=uri)
    project_drop_resources(
        client,
        project_name,
        database_name,
        role_name,
        user_name,
    )


@database_app.command("list")
def database_list(
    uri: Annotated[
        str,
        typer.Option(
            envvar="MILVUS_URI",
            help="URI of the Milvus gRPC endpoint, e.g. 'http://root:Milvus@localhost:19530'",
        ),
    ],
):
    """List all databases and their collections."""
    client = MilvusClient(uri=uri)
    database_list_all(client)
