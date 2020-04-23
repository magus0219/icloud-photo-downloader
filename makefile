clean :
	rm -rf cov_html
	rm -rf *.log

test : clean
	python -m pytest --cov-report term --cov-report html:cov_html --cov=artascope/src

check:
	pre-commit run --all-file

release:
	@echo tag $(VER)
	@echo $(VER) > .project_version
	git add .project_version
	git commit .project_version -m "release new version $(VER)"
	git tag $(VER)
	git push --tags
