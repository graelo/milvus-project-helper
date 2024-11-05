from typing_extensions import Annotated
from dataclasses import dataclass

import typer
from pymilvus import MilvusClient

app = typer.Typer(no_args_is_help=True)


@dataclass
class ProjectResourceNaming:
    project_name: str
    database_name: str
    role_name: str
    user_name: str
    user_password: str


def check_password_strength(password: str):
    """Check if the password is strong enough according to Milvus requirements."""
    if len(password) < 8:
        typer.echo("Password must be at least 8 characters long")
        raise typer.Exit(code=1)
    if not any(c.isupper() for c in password):
        typer.echo("Password must contain at least one uppercase letter")
        raise typer.Exit(code=1)
    if not any(c.islower() for c in password):
        typer.echo("Password must contain at least one lowercase letter")
        raise typer.Exit(code=1)
    if not any(c.isdigit() for c in password):
        typer.echo("Password must contain at least one digit")
        raise typer.Exit(code=1)
    if not any(c in "!@#$%^&*()-+" for c in password):
        typer.echo("Password must contain at least one special character")
        raise typer.Exit(code=1)


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
            typer.echo(
                f"Database {rn.database_name} already exists, skipping creation."
            )
        else:
            typer.echo(f"Database {rn.database_name} already exists.")
            raise typer.Exit(code=1)
    else:
        client.create_database(rn.database_name)

    # 2. Create project user
    if client.user_exists(rn.user_name):
        if skip_if_exists:
            typer.echo(f"User {rn.user_name} already exists, skipping creation.")
        else:
            typer.echo(f"User {rn.user_name} already exists.")
            raise typer.Exit(code=1)
    else:
        client.create_user(user_name=rn.user_name, password=rn.user_password)

    # 3. Create project role in the database
    if client.role_exists(rn.role_name):
        if skip_if_exists:
            typer.echo(f"Role {rn.role_name} already exists, skipping creation.")
        else:
            typer.echo(f"Role {rn.role_name} already exists.")
            raise typer.Exit(code=1)
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
        typer.echo(f"Privilege already granted to role {rn.role_name}.")

    # 5. Bind role to user
    if not client.has_role(user_name=rn.user_name, role_name=rn.role_name):
        client.grant_role(user_name=rn.user_name, role_name=rn.role_name)
    else:
        typer.echo(f"Role {rn.role_name} already granted to user {rn.user_name}.")


@app.command()
def setup_project(
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
    recreate: bool = typer.Option(
        False,
        help="Drop and recreate the project resources if they already exist",
    ),
    skip_if_exists: bool = typer.Option(
        False,
        help="Skip creation if the resource already exists",
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
    typer.echo(f"Setting up project `{project_name}`...")

    if not user_password:
        user_password = typer.prompt("Enter password for the new user", hide_input=True)
    assert user_password is not None and user_password != ""
    check_password_strength(user_password)

    resource_names = ProjectResourceNaming(
        project_name=project_name,
        database_name=database_name or f"db_{project_name}",
        role_name=role_name or f"role_{project_name}",
        user_name=user_name or f"user_{project_name}",
        user_password=user_password,
    )

    # Print the resource names in a nice table instead of basic typer.echo
    for k, v in resource_names.__dict__.items():
        typer.echo(f"  {k}: {v}")

    if dry_run:
        typer.echo("Dry run: exiting without executing commands")
        return

    client = MilvusClient(uri=uri)
    setup_project_resources(
        client, resource_names, recreate=recreate, skip_if_exists=skip_if_exists
    )


@app.command()
def change_password():
    print("Changing password...")
