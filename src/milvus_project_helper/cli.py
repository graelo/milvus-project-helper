"""Command Line Interface for Milvus project management.

This module implements the CLI commands for managing Milvus projects:
- project create: Create a new project with associated resources
- project describe: Show details about an existing project
- project drop: Remove a project and its resources
- project change-password: Change a user's password
- database list: List all databases and their collections

All commands support the MILVUS_URI environment variable for connection settings.
"""

from __future__ import annotations

import logging

import typer
from pymilvus import MilvusClient
from typing_extensions import Annotated

from . import database, project, utils

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
            help="URI of the Milvus gRPC endpoint, e.g. 'http://root:Milvus@localhost:19530'."
            "The user must be able to create databases, roles and users",
        ),
    ],
    yes: Annotated[
        bool,
        typer.Option(
            "--yes",
            "-y",
            help="Skip confirmation prompt",
        ),
    ] = False,
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
        None | str,
        typer.Option(help="Password for the new user"),
    ] = None,
    project_name: Annotated[
        str,
        typer.Argument(help="New project name"),
    ] = "new-project",
) -> None:
    """Create a new project with associated resources."""
    logger.info(f"\nSetting up project '{project_name}':")
    logger.info("─" * 50)

    # Build resource names first, use placeholder for password in dry-run
    resource_names = project.ResourceNaming(
        project_name=project_name,
        database_name=database_name or f"db_{project_name}",
        role_name=role_name or f"role_{project_name}",
        user_name=user_name or f"user_{project_name}",
        user_password=user_password or "",
    )

    logger.info("\nResource naming:")
    for k, v in resource_names.__dict__.items():
        if k == "user_password":
            logger.info(f"  • {k}: {'(not yet set)'}")
        else:
            logger.info(f"  • {k}: {v}")

    if not yes and not typer.confirm("\nDo you want to proceed?", default=True):
        logger.info("Operation cancelled.")
        raise typer.Exit()

    # Only prompt for password when actually creating resources
    if not resource_names.user_password:
        logger.info("")
        resource_names.user_password = typer.prompt(
            "Enter password for the new user",
            hide_input=True,
            confirmation_prompt=True,  # Ask user to type twice
            show_default=False,
            show_choices=False,
        )
    assert resource_names.user_password != ""

    try:
        utils.check_password_strength(resource_names.user_password)
    except utils.PasswordStrengthError as e:
        typer.echo("❌ " + str(e))  # Keep typer.echo for error messages
        raise typer.Exit(code=1)

    client = MilvusClient(uri=uri)

    try:
        project.create_resources(
            client,
            resource_names,
        )
    except project.ResourceExistsError as e:
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
        str,
        typer.Argument(help="Name of the project to list resources for"),
    ],
    user_name: Annotated[
        None | str,
        typer.Option(
            help="Name of the user to check privileges for (default: check all users)",
        ),
    ] = None,
) -> None:
    """List resources for a project."""
    logger.info(f"Listing resources for project `{project_name}`...")

    client = MilvusClient(uri=uri)

    project.describe_resources(client, project_name, user_name)


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
    yes: Annotated[
        bool,
        typer.Option(
            "--yes",
            "-y",
            help="Skip confirmation prompt",
        ),
    ] = False,
) -> None:
    """Drop a project and its resources."""
    db_name = database_name or f"db_{project_name}"
    logger.info(f"About to drop project `{project_name}` (database: {db_name})")

    if not yes and not typer.confirm(
        "\nAre you sure you want to proceed?",
        default=False,
    ):
        logger.info("Operation cancelled.")
        raise typer.Exit()

    client = MilvusClient(uri=uri)
    project.drop_resources(
        client,
        project_name,
        database_name,
    )


@project_app.command("change-password")
def project_change_password(
    uri: Annotated[
        str,
        typer.Option(
            envvar="MILVUS_URI",
            help="URI of the Milvus gRPC endpoint, e.g. 'http://root:Milvus@localhost:19530'",
        ),
    ],
    project_name: Annotated[str, typer.Argument(help="Name of the project")],
    user_name: Annotated[
        str,
        typer.Option(
            help="Name of the user to change password for (default: check all users)",
        ),
    ],
    old_password: Annotated[
        None | str,
        typer.Option(help="Old password for the user"),
    ] = None,
    new_password: Annotated[
        None | str,
        typer.Option(help="New password for the user"),
    ] = None,
) -> None:
    """Change password for a user in a project."""
    try:
        client = MilvusClient(uri=uri)

        if not old_password:
            logger.info("")
            old_password = typer.prompt(
                f"Enter old password for user `{user_name}`",
                hide_input=True,
                show_default=False,
                show_choices=False,
            )
        assert old_password is not None and old_password != ""

        if not new_password:
            logger.info("")
            new_password = typer.prompt(
                "Enter new password for user `{user_name}`",
                hide_input=True,
                confirmation_prompt=True,  # Ask user to type twice
                show_default=False,
                show_choices=False,
            )
        assert new_password is not None and new_password != ""

        # Validate the new password
        utils.check_password_strength(new_password)

        project.change_user_password(
            client=client,
            project_name=project_name,
            user_name=user_name,
            old_password=old_password,
            new_password=new_password,
        )
    except Exception as e:
        typer.echo(f"Error: {e!s}", err=True)
        raise typer.Exit(1)


@database_app.command("list")
def database_list(
    uri: Annotated[
        str,
        typer.Option(
            envvar="MILVUS_URI",
            help="URI of the Milvus gRPC endpoint, e.g. 'http://root:Milvus@localhost:19530'",
        ),
    ],
) -> None:
    """List all databases and their collections."""
    client = MilvusClient(uri=uri)
    database.list_all(client)
