# Use an official Python runtime as a parent image
FROM nas.magicqin.com:5555/magicqin/images/python:base-latest

# Set the working directory to /app
WORKDIR /app

# Install any needed packages specified in Pipfile
RUN pip3 install -i https://mirrors.aliyun.com/pypi/simple/ --upgrade pip
RUN pip3 install -i https://mirrors.aliyun.com/pypi/simple/ pipenv
COPY Pipfile* /app/
RUN PIPENV_PYPI_MIRROR=https://mirrors.aliyun.com/pypi/simple/ pipenv install --system --deploy -d

# Copy the current directory contents into the container at /app
COPY . /app

# Make port 8888 available to the world outside this container
#EXPOSE 8888

## Define environment variable
ENV PYTHONPATH .
ENV PYTHONUNBUFFERED 1

ENTRYPOINT ["/app/docker-entrypoint.sh"]
CMD ["web"]
