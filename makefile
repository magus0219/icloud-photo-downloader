clean :
	rm -rf cov_html
	rm -rf *.log

test : clean
	ARTASCOPE_ENV=localtest pipenv run pytest --cov=artascope/src --cov-report term --cov-report html:cov_html

check:
	pipenv run pre-commit run --all-file

release:
	@echo tag $(VER)
	@echo $(VER) > .project_version
	git add .project_version
	git commit .project_version -m "release new version $(VER)"
	git tag -a -m "release new version $(VER)" $(VER)
	git push origin --follow-tags
