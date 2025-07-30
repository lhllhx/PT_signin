import asyncio
import io
import os
import shutil
from base64 import b64encode
from pathlib import Path
from zipfile import ZipFile

import aiohttp

import flexget


def handler(event, context) -> str:
    asyncio.run(main())
    return 'success'


async def main() -> None:
    os.chdir('/tmp')
    async with aiohttp.ClientSession(
        headers={'Authorization': f'Bearer {os.environ['GITHUB_TOKEN']}'},
        base_url='https://api.github.com',
    ) as session:
        await download(session, os.environ['PLUGIN_REPO'], os.environ['CONFIG_REPO'])
        flexget.main(['execute'])
        await upload(session, ['db-config.sqlite', 'flexget.log'], os.environ['CONFIG_REPO'])


async def download(session: aiohttp.ClientSession, plugin_repo: str, config_repo: str) -> None:
    async def download_plugins() -> None:
        async with session.get(f'https://github.com/{plugin_repo}/archive/master.zip') as response:
            assert response.status == 200, 'failed to retrieve the plugin repository'
            with ZipFile(io.BytesIO(await response.read())) as zip_file:
                zip_file.extractall()
        plugin_path = Path('plugins')
        # TODO: remove ignore_errors on Python 3.13+
        shutil.rmtree(plugin_path, ignore_errors=True)
        Path(zip_file.namelist()[0]).rename(plugin_path)

    async def download_config() -> None:
        async with session.get(f'repos/{config_repo}/contents/config.yml') as response:
            assert response.status == 200, 'failed to retrieve config.yml'
            Path('config.yml').write_bytes(await response.read())

    async def download_db() -> None:
        async with session.get(f'repos/{config_repo}/contents/db-config.sqlite') as response:
            if response.status == 200:
                Path('db-config.sqlite').write_bytes(await response.read())

    session.headers['Accept'] = 'application/vnd.github.raw+json'
    async with asyncio.TaskGroup() as tg:
        for func in [download_plugins, download_config, download_db]:
            tg.create_task(func())


async def upload(session: aiohttp.ClientSession, filenames: list[str], config_repo: str) -> None:
    owner, name = config_repo.split('/')
    query = f"""
        {{
          repository(owner: "{owner}", name: "{name}") {{
            defaultBranchRef {{
              id
              target {{
                ... on Commit {{
                  history(first: 1) {{
                    nodes {{
                      oid
                    }}
                  }}
                }}
              }}
            }}
          }}
        }}"""
    async with session.post('graphql', json={'query': query}) as resp:
        branch = (await resp.json())['data']['repository']['defaultBranchRef']
        branch_id = branch['id']
        head_oid = branch['target']['history']['nodes'][0]['oid']
    query = """
        mutation ($input: CreateCommitOnBranchInput!) {
          createCommitOnBranch(input: $input) {
            commit {
              url
            }
          }
        }"""
    variables = {
        'variables': {
            'input': {
                'branch': {'id': branch_id},
                'message': {'headline': 'FlexGet run'},
                'fileChanges': {
                    'additions': [
                        {
                            'path': filename,
                            'contents': b64encode(Path(filename).read_bytes()).decode(),
                        }
                        for filename in filenames
                    ]
                },
                'expectedHeadOid': head_oid,
            }
        }
    }
    async with session.post('graphql', json={'query': query, **variables}) as resp:
        assert resp.status == 200, 'upload failed'
