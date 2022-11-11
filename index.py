import os
import zipfile
import requests
import base64
from flexget import main
import json

github_date_repository=os.environ['github_date_repository']
github_token=os.environ['github_token']
def handler(event, context):
    #os.mkdir("./tmp/plugins")
    try:
        os.chdir('/tmp')
        os.mkdir("/tmp/pass")
    except:
        pass
    headers={}
    headers["Authorization"] = 'Bearer '+ github_token
    headers["Accept"]='application/vnd.github.v3.raw'
    #plugins_path = os.path.join('./tmp/','plugins')
    #plugins_path = os.path.join('/','tmp')
    plugins_path = "/tmp"
    plugins_file = plugins_path + '/plugins.zip'
    plugins_url =  "https://github.com/lhllhx/flexget_qbittorrent_mod/archive/refs/heads/master.zip"
    plugins=requests.get(plugins_url,headers=headers)
    with open(plugins_file, 'wb') as f:
        f.write(plugins.content)
        f.close()
    with zipfile.ZipFile(plugins_file, 'r') as zip_ref:
        zip_ref.extractall(plugins_path)
    os.rename(plugins_path + '/flexget_qbittorrent_mod-master', plugins_path + '/plugins')
    print("plugins done")

    #download_path = os.path.join('/tmp/','pass')
    download_path = "/tmp"
    download_file = download_path + '/config.zip'
    date_url='https://api.github.com/repos/' + github_date_repository + '/contents/config.zip'    
    headers["Accept"]='application/vnd.github.v3.raw'
    date=requests.get(date_url, headers=headers)
    with open(download_file, 'wb') as f:
        f.write(date.content)
        f.close()
    zipFile = zipfile.ZipFile('/tmp/config.zip')
    zipFile.extract('config.yml','/tmp')
    try:
        zipFile.extract('db-config.sqlite','/tmp') 
    except:
        print("first run")
    print("data download done")

    os.chdir('/tmp') 
    avg={'execute'}
    main(avg)
    print("flexget run done")
    #os.remove('./pass/config.zip')
    files = ['db-config.sqlite', 'config.yml','flexget.log']
    with zipfile.ZipFile('config.zip', mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
      for fn in files:
           zf.write(fn)
    with open('config.zip', 'rb') as f:
      encode_zip = base64.b64encode(f.read())
      f.close()
      
    print("zip done")
    headers["Accept"]='application/vnd.github+json'
    date=requests.get(date_url, headers=headers)
    sha=date.json()['sha']

    headers["Accept"]='application/vnd.github+json'
    update={}
    update["message"]="update config"
    update["committer"]={"name":"autoupdate","email":"octocat@github.com"}
    update["content"]=encode_zip.decode('utf-8')
    update["sha"]=sha
    print(update["committer"]["name"])
    res=requests.put(date_url, headers=headers, data=json.dumps(update))
    print("all done")
