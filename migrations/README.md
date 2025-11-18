git add <path_to_file>
git commit -m '<your_msg>'

git branch <branch_name> - create a new branch
git checkout -b <branch_name> - create a new branch a switch to it


alembic init migrations - run once to init migration engine

alembic revision --autogenerate -m "<your_migration_message>" - create migration scenario alembic upgrade head - run migrations scripts