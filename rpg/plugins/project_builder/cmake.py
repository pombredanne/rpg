from rpg.command import Command
from rpg.plugin import Plugin
from rpg.utils import str_to_pkgname
import logging
import re


class CMakePlugin(Plugin):

    def extracted(self, project_dir, spec, sack):
        if (project_dir / "CMakeLists.txt").is_file():
            regex = re.compile(
                r"project\s*\((.*?)(?:\s(.*?))?[\s\)]",
                re.IGNORECASE | re.DOTALL)
            with (project_dir / "CMakeLists.txt").open() as f:
                result = regex.search(f.read())
                if result.group(1):
                    spec.Name = str_to_pkgname(result.group(1))
                if result.group(2):
                    spec.Version = result.group(2)

    def patched(self, project_dir, spec, sack):
        """ Appends commands to build Project with CMake build system """
        if (project_dir / "CMakeLists.txt").is_file():
            spec.BuildRequires.add("cmake")
            logging.debug('CMakeLists.txt found')
            build = Command()
            build.append("cmake .")
            build.append("%{make_build}")
            install = Command('make install DESTDIR="$RPM_BUILD_ROOT"')
            _parse(project_dir, spec)
            spec.build = build
            spec.install = install

    def compiled(self, project_dir, spec, sack):
        """ Finds (not only for build) dependencies from CMakeCache """
        regex = re.compile(r":FILEPATH=(/\S*)")
        cache_files = list(project_dir.glob("**/CMakeCache.txt"))
        matches = []
        for p in cache_files:
            with p.open() as f:
                matches += regex.findall(f.read())
        matches = set(matches)
        spec.build_required_files.update(matches)
        spec.required_files.update(matches)


def _parse(project_dir, spec):
    regex = re.compile(r"\#(?!\[\[)[^\n]*ENABLE_TESTING.*?(?:\n|$)|"
                       r"\#\[\[.*?ENABLE_TESTING.*?\]\]|"
                       r"ENABLE_TESTING", re.DOTALL)
    cmake_files = list(project_dir.glob("**/CMakeLists.txt"))
    matches = []
    for element in cmake_files:
        with element.open() as f:
            matches += regex.findall(f.read())
            if "ENABLE_TESTING" in matches:
                spec.check.append("make test ARGS='-V %{?_smp_mflags}'")
                return
