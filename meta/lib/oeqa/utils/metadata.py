# Copyright (C) 2016 Intel Corporation
#
# Released under the MIT license (see COPYING.MIT)
#
# Functions to get metadata from the testing host used
# for analytics of test results.

from collections import OrderedDict
from collections.abc import MutableMapping
from xml.dom.minidom import parseString
from xml.etree.ElementTree import Element, tostring

from oeqa.utils.commands import runCmd, get_bb_vars

def get_os_release():
    """Get info from /etc/os-release as a dict"""
    data = OrderedDict()
    os_release_file = '/etc/os-release'
    if not os.path.exists(os_release_file):
        return None
    with open(os_release_file) as fobj:
        for line in fobj:
            key, value = line.split('=', 1)
            data[key.strip().lower()] = value.strip().strip('"')
    return data

def metadata_from_bb():
    """ Returns test's metadata as OrderedDict.

        Data will be gathered using bitbake -e thanks to get_bb_vars.
    """
    metadata_config_vars = ('MACHINE', 'BB_NUMBER_THREADS', 'PARALLEL_MAKE')

    info_dict = OrderedDict()
    hostname = runCmd('hostname')
    info_dict['hostname'] = hostname.output
    data_dict = get_bb_vars()

    # Distro information
    info_dict['distro'] = {'id': data_dict['DISTRO'],
                           'version_id': data_dict['DISTRO_VERSION'],
                           'pretty_name': '%s %s' % (data_dict['DISTRO'], data_dict['DISTRO_VERSION'])}

    # Host distro information
    os_release = get_os_release()
    if os_release:
        info_dict['host_distro'] = OrderedDict()
        for key in ('id', 'version_id', 'pretty_name'):
            if key in os_release:
                info_dict['host_distro'][key] = os_release[key]

    info_dict['layers'] = get_layers(data_dict['BBLAYERS'])
    info_dict['bitbake'] = git_rev_info(os.path.dirname(bb.__file__))

    info_dict['config'] = OrderedDict()
    for var in sorted(metadata_config_vars):
        info_dict['config'][var] = data_dict[var]
    return info_dict

def metadata_from_data_store(d):
    """ Returns test's metadata as OrderedDict.

        Data will be collected from the provided data store.
    """
    # TODO: Getting metadata from the data store would
    # be useful when running within bitbake.
    pass

def git_rev_info(path):
    """Get git revision information as a dict"""
    from git import Repo, InvalidGitRepositoryError, NoSuchPathError

    info = OrderedDict()
    try:
        repo = Repo(path, search_parent_directories=True)
    except (InvalidGitRepositoryError, NoSuchPathError):
        return info
    info['commit'] = repo.head.commit.hexsha
    info['commit_count'] = repo.head.commit.count()
    try:
        info['branch'] = repo.active_branch.name
    except TypeError:
        info['branch'] = '(nobranch)'
    return info

def get_layers(layers):
    """Returns layer information in dict format"""
    layer_dict = OrderedDict()
    for layer in layers.split():
        layer_name = os.path.basename(layer)
        layer_dict[layer_name] = git_rev_info(layer)
    return layer_dict

def write_metadata_file(file_path, metadata):
    """ Writes metadata to a XML file in directory. """

    xml = dict_to_XML('metadata', metadata)
    xml_doc = parseString(tostring(xml).decode('UTF-8'))
    with open(file_path, 'w') as f:
        f.write(xml_doc.toprettyxml())

def dict_to_XML(tag, dictionary, **kwargs):
    """ Return XML element converting dicts recursively. """

    elem = Element(tag, **kwargs)
    for key, val in dictionary.items():
        if tag == 'layers':
            child = (dict_to_XML('layer', val, name=key))
        elif isinstance(val, MutableMapping):
            child = (dict_to_XML(key, val))
        else:
            if tag == 'config':
                child = Element('variable', name=key)
            else:
                child = Element(key)
            child.text = str(val)
        elem.append(child)
    return elem
