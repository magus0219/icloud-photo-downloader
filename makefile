clean :
	rm -rf cov_html
#	rm -rf *.log

test : clean
	python -m pytest --cov-report term --cov-report html:cov_html --cov=artascope/src

check:
	pre-commit run --all-file
