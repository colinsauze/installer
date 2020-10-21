from __future__ import print_function, unicode_literals

import argparse
import os
import os.path
import stat
import sys
from shutil import copyfile
from subprocess import check_call
try:
    from urllib.request import urlretrieve
except ImportError:
    from urllib import urlretrieve
from zipfile import ZipFile

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("csp", help="Which cloud provider to install into")
    parser.add_argument("--dry-run", help="Perform a dry run", action="store_true")
    args = parser.parse_args()

    tf_repo_zip, _ = urlretrieve("https://github.com/clusterinthecloud/terraform/archive/master.zip")
    ZipFile(tf_repo_zip).extractall()
    os.chdir("terraform-master")

    if sys.platform.startswith("linux"):
        tf_platform = "linux_amd64"
    elif sys.platform == "darwin":
        tf_platform = "darwin_amd64"
    elif sys.platform == "win32":
        raise NotImplementedError("Windows is not supported at the mooment")
    else:
        raise NotImplementedError("Platform is not supported")

    tf_version = "0.12.29"
    tf_template = "https://releases.hashicorp.com/terraform/{v}/terraform_{v}_{p}.zip"
    tf_url = tf_template.format(v=tf_version, p=tf_platform)
    tf_zip, _ = urlretrieve(tf_url)
    ZipFile(tf_zip).extractall()
    os.chmod("terraform", stat.S_IRWXU)

    if not os.path.isfile("citc-key"):
        check_call(["ssh-keygen", "-t", "rsa", "-f", "citc-key", "-N", ""])

    check_call(["./terraform", "init", args.csp])
    check_call(["./terraform", "validate", args.csp])

    config_file(args.csp)

    if not args.dry_run:
        check_call(["./terraform", "apply", args.csp])


def config_file(csp):
    with open(os.path.join(csp, "terraform.tfvars.example")) as f:
        config = f.read()

    if csp == "aws":
        config = aws_config_file(config)
    else:
        raise NotImplementedError("Other providers are not supported yet")

    if "ANSIBLE_BRANCH" in os.environ:
        config = config + '\nansible_branch = "{}"'.format(os.environ["ANSIBLE_BRANCH"])

    with open("terraform.tfvars", "w") as f:
        f.write(config)


def aws_config_file(config):
    config = config.replace("~/.ssh/aws-key", "citc-key")
    with open("citc-key.pub") as pub_key:
        pub_key_text = pub_key.read().strip()
    config = config.replace("admin_public_keys = <<EOF", "admin_public_keys = <<EOF\n" + pub_key_text)
    return config


if __name__ == "__main__":
    main()
