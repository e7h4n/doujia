test:
	@uv run coverage run -m pytest
	@uv run coverage report
	@uv run coverage xml

lint:
	@uv run ruff check .

commit:
	@git add .
	@git commit -m 'change'
	@git push

rebuild-env:
	git clean -dfx
	uv sync
	uv run pre-commit installuv
