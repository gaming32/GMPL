import os
import zipfile, json, markdown, _thread
from urllib import request

info_template = {
    'name': 'modpack',
    'site': None,
    'description': '',
    'author': {
        'name': 'person',
        'site': None
    }
}


def create_gmpl_file(mod_paths=[], mod_ids=[], dest_file='modpack.gmpl',
        info=info_template, resources_paths=[], resources_ids=[], config_paths=[]):
    "Mod IDS are tuple(CurseForge mod id, CurseForge download id)"
    file = zipfile.ZipFile(dest_file, 'w', zipfile.ZIP_DEFLATED)
    info = info.copy()

    for path in mod_paths:
        print(path)
        file.write(path, 'mods/%s' % os.path.basename(path))
    download_mods = file.open('downloads', 'w')
    for mod_id in mod_ids:
        print(mod_id)
        mod_id = tuple(mod_id)
        if len(mod_id) > 1:
            download_mods.write(
                ('https://api.cfwidget.com/mc-mods/minecraft/%s|%s\n' % mod_id).encode())
        else:
            download_mods.write(
                ('https://api.cfwidget.com/mc-mods/minecraft/%s\n' % mod_id).encode())
    download_mods.close()

    for path in resources_paths:
        print(path)
        file.write(path, 'resourcepacks/%s' % os.path.basename(path))
    download_resources = file.open('download_resourcepacks', 'w')
    for resource_id in resources_ids:
        print(resource_id)
        resource_id = tuple(resource_id)
        if len(resource_id) > 1:
            download_resources.write(
                ('https://api.cfwidget.com/texture-packs/minecraft/%s|%s\n' % resource_id).encode())
        else:
            download_resources.write(
                ('https://api.cfwidget.com/texture-packs/minecraft/%s\n' % resource_id).encode())
    download_resources.close()

    for path in config_paths:
        file.write(path, 'config/%s' % os.path.basename(path))

    file.writestr('info.json', json.dumps(info))
    file.close()


class GmplFile:
    def __init__(self, path):
        self.zip = zipfile.ZipFile(path, 'r', zipfile.ZIP_DEFLATED)
    def close(self): self.zip.close()
    def __del__(self): self.close()

    @property
    def info(self):
        if hasattr(self, '_info'):
            return self._info
        else:
            info = json.loads(self.zip.read('info.json').decode())
            self._info = info
            return info

    @property
    def name(self):
        if hasattr(self, '_name'):
            return self._name
        else:
            name = self.info['name']
            self._name = name
            return name

    @property
    def site(self):
        if hasattr(self, '_site'):
            return self._site
        else:
            site = self.info['site']
            self._site = site
            return site

    @property
    def description(self):
        if hasattr(self, '_description'):
            return self._description
        else:
            description = self.info['description']
            self._description = description
            return description

    @property
    def author_name(self):
        if hasattr(self, '_author_name'):
            return self._author_name
        else:
            author_name = self.info['author']['name']
            self._author_name = author_name
            return author_name

    @property
    def author_site(self):
        if hasattr(self, '_author_site'):
            return self._author_site
        else:
            author_site = self.info['author']['site']
            self._author_site = author_site
            return author_site

    def _ynstr(self, string='href="%s"', base=''):
        if base: return string % base
        else: return ''

    def pretty_html(self, template=None):
        if template is None:
            template = """<html>
  <h2><a %s>%s</a></h2>
  <div style="color:gray"><i><small>by <a %s>%s</a></small></i></div>
  %s
</html>"""
        return template % (self._ynstr(base=self.site), self.name,
            self._ynstr(base=self.author_site), self.author_name,
            markdown.markdown(self.description))

    def _extract(self, dest1, dest2):
        for file in self.zip.namelist():
            if file.startswith('%s/' % dest1):
                self.zip.extract(file, dest2)
    def extract_mods(self, dest):
        self._extract('mods', dest)
    def extract_resourcepacks(self, dest):
        self._extract('resourcepacks', dest)

    def _download(self, src, dest1, dest2):
        dest = os.path.join(dest1, dest2)
        for url in self.zip.open(src):
            url = url.decode().strip()
            if '|' in url:
                url, version_id = url.split('|')
            else: version_id = None
            info = json.loads(request.urlopen(url).read())
            versions = info['files']
            if version_id is None:
                version = info['download']
            else:
                for check_version in versions:
                    if check_version['id'] == int(version_id):
                        version = check_version
                        break
            version_name = version['name']
            url_to_download = 'https://media.forgecdn.net/files/%s/%s/%s' % (version_id[:4], version_id[-3:], version_name)
            open(os.path.join(dest, version_name), 'wb').write(request.urlopen(url_to_download).read())
    def download_mods(self, dest):
        self._download('downloads', dest, 'mods')
    def download_resourcepacks(self, dest):
        self._download('download_resourcepacks', dest, 'resourcepacks')
    
    def inject(self, dest):
        self.extract_mods(dest)
        self.download_mods(dest)
        self.extract_resourcepacks(dest)
        self.download_resourcepacks(dest)

    def _inject_threaded(self, dest, prog_cb):
        prog_cb('Extracting mods...')
        self.extract_mods(dest)
        prog_cb('Downloading mods...')
        self.download_mods(dest)
        prog_cb('Extracting resource packs...')
        self.extract_resourcepacks(dest)
        prog_cb('Downloading resource packs...')
        self.download_resourcepacks(dest)
        prog_cb('Done')
    def inject_threaded(self, dest, prog_cb=(lambda x: None)):
        _thread.start_new_thread(self._inject_threaded, (dest, prog_cb))