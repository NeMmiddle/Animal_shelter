# Animal_shelter

### *Don't forget to change the data in the file .env. An example of filling is in the env_example file.*      
&nbsp; 
### You can run it as it is usually done:
```
python3 -m venv venv

source venv/bin/activate
```
### After activating the environment, install the dependencies:
```
pip install -r requirements.txt
```

### In order for the photos to be saved on Google drive, you need to follow this [instructions](https://developers.google.com/drive/api/quickstart/python). As a result, we will download a json file that Google will provide us with and all we need is to add it to the root folder of our project:
### Sample file. You can find the same example in the file: [client_secret_example.json](https://github.com/NeMmiddle/Animal_shelter/blob/master/client_secret_exemple.json):
```
{
  "web": {
    "client_id": "YOUR CLIENT ID",
    "project_id": "YOUR PROJECT ID",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_secret": "YOUR CLIENT SECRET",
    "redirect_uris": [
      "http://localhost:8000/",
      "http://localhost:8080/"
    ],
    "javascript_origins": [
      "http://localhost:8080",
      "http://localhost:8000"
    ]
  }
}
```
### After that, you can run the project with the command:
```
uvicorn main:app --reload
```



