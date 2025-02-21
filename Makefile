test:
	@pdm run coverage run -m pytest
	@pdm run coverage report
	@pdm run coverage xml

lint:
	@pdm run ruff check .

format:
	@pdm run pre-commit run --all accounting-style
	@pdm run pre-commit run --all bean-format
	@pdm run pre-commit run --all bean-check

commit:
	@git add .
	@git commit -m 'change'
	@git push

rebuild-env:
	git clean -dfx
	pdm install -d
	pdm run pre-commit install
