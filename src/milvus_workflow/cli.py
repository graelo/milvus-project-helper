from typing_extensions import Annotated

import typer
from pymilvus import MilvusClient
from core import ProjectResourceNaming, check_password_strength, setup_project_resources, PasswordStrengthError, ResourceExistsError

app = typer.Typer(no_args_is_help=True)

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
    #
    #
    dry_run: bool = typer.Option(
        True,
        help="Print the commands that would be executed without actually running them",
    ),
    #
    #
    recreate: bool = typer.Option(
        False,
        help="Drop and recreate the project resources if they already exist",
    ),
    #
    #
    skip_if_exists: bool = typer.Option(
        False,
        help="Skip creation if the resource already exists",
    ),
    #
    #
    database_name: Annotated[
        None | str,
        typer.Option(
            help="Name of the database to use for the project "
            "(default: 'db_<project_name>')",
        ),
    ] = None,
    #
    #
    role_name: Annotated[
        None | str,
        typer.Option(
            help="Name of the role to use for the project "
            "(default: 'role_<project_name>')",
        ),
    ] = None,
    #
    #
    user_name: Annotated[
        None | str,
        typer.Option(
            help="Name of the user to use for the project "
            "(default: 'user_<project_name>')",
        ),
    ] = None,
    #
    #
    user_password: Annotated[
        None | str, typer.Option(help="Password for the new user")
    ] = None,
    #
    #
    project_name: Annotated[
        str, typer.Argument(help="New project name")
    ] = "new-project",
):
    typer.echo(f"Setting up project `{project_name}`...")
    if not user_password:
        user_password = typer.prompt("Enter password for the new user", hide_input=True)
    assert user_password is not None and user_password != ""
    
    try:
        check_password_strength(user_password)
    except PasswordStrengthError as e:
        typer.echo(str(e))
        raise typer.Exit(code=1)
    
    resource_names = ProjectResourceNaming(
        project_name=project_name,
        database_name=database_name or f"db_{project_name}",
        role_name=role_name or f"role_{project_name}",
        user_name=user_name or f"user_{project_name}",
        user_password=user_password,
    )
    
    for k, v in resource_names.__dict__.items():
        typer.echo(f"  {k}: {v}")
    
    if dry_run:
        typer.echo("Dry run: exiting without executing commands")
        return
    
    client = MilvusClient(uri=uri)
    
    try:
        setup_project_resources(
            client, resource_names, recreate=recreate, skip_if_exists=skip_if_exists
        )
    except ResourceExistsError as e:
        typer.echo(str(e))
        raise typer.Exit(code=1)