# Milvus Project Helper

A CLI tool for managing Milvus database projects with proper resource isolation
and access control.

## Features

- Create isolated projects with dedicated databases, roles, and users
- Manage project resources and user privileges
- List and describe database resources
- Change user passwords with strong password validation
- Clean project deletion with resource cleanup

## Installation

```bash
pip install milvus-project-helper
```

## Usage

The tool supports connection to Milvus via the `MILVUS_URI` environment variable
or `--uri` option.

### Creating a Project

Create a new project with associated database, role and user:

```sh
$ milvus-project-helper project create myproject --user-name alice -y

Setting up project 'myproject':
──────────────────────────────────────────────────

Resource naming:
  • project_name: myproject
  • database_name: db_myproject
  • role_name: role_myproject
  • user_name: alice
  • user_password: (not yet set)

Enter password for the new user: ***
Repeat for confirmation: ***

Project resources for 'myproject':
──────────────────────────────────────────────────
  × database: db_myproject
  • Created database
  × user: alice
  × role: role_myproject
  • Created user
  • Created role

Granting privileges:
  • CreateIndex on Collection
  • Load on Collection
  • Insert on Collection
  • Delete on Collection
  • Search on Collection
  • Query on Collection
  • Flush on Collection

Assigned role 'role_myproject' to user 'alice'
```

### Listing Databases

View all databases and their collections:

```sh
$ milvus-project-helper database list
Found 2 databases:

Database: default
  Collections: []

Database: db_myproject
  Collections: []
```

### Dropping a Project

Remove a project and all its resources:

```sh
$ milvus-project-helper project drop myproject
About to drop project `myproject` (database: db_myproject)

Are you sure you want to proceed? [y/N]: y

Project resources for 'myproject':
──────────────────────────────────────────────────
  ✓ database: db_myproject

Dropping resources:
  • Dropped user 'alice'
  • Dropped role 'role_myproject'
  • Dropped database 'db_myproject'
```

## Environment Variables

- `MILVUS_URI`: URI of the Milvus gRPC endpoint (e.g. `'http://root:Milvus@localhost:19530'`)

## Password Requirements

All user passwords must meet these requirements:

- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one digit
- At least one special character from: !@#$%^&*()-+

## License

MIT

