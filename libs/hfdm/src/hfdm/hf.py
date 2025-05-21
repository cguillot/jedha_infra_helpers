from contextlib import contextmanager

import logging
import traceback

from pathlib import Path
import tempfile
import shutil
import re
from typing import Generator

import yaml

from huggingface_hub import HfApi
from huggingface_hub.errors import RepositoryNotFoundError

from hfdm.utils import VariableProvider, VariableReplacer

logger = logging.getLogger(__name__)


class HuggingFaceSpaceDeployment:
    def __init__(self, deployment_config_yaml_path: Path):
        # load data
        with open(deployment_config_yaml_path, "r", encoding="utf-8") as file:
            self.deployment_data = yaml.safe_load(file)

        self.deployment_name = self.deployment_data.get("hf-deploy", {}).get(
            "name", None
        )
        self.deployment_src_root_path = (
            Path(deployment_config_yaml_path).resolve().parent
        )

        logger.info(
            "HuggingFace deployment %s loaded from source folder: %s",
            self.deployment_name,
            self.deployment_src_root_path,
        )

    def get_deployment_name(self):
        return self.deployment_name

    @contextmanager
    def temp_deployment_folder(self) -> Generator[str, None, None]:
        """Return the tempory folder hosting proper mirroring of space content

        Yields:
            Generator[str, None, None]: temp folder path
        """
        tmpdir = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        try:
            tmpdir_name = tmpdir.name
            self.__prepare_hf_mirror(tmpdir_name)

            yield tmpdir_name
        finally:
            tmpdir.cleanup()

    def __prepare_hf_mirror(self, target_root):
        """Copy files and directories based on YAML configuration."""
        yaml_data = self.deployment_data
        base_path = self.deployment_src_root_path

        content = yaml_data.get("hf-deploy", {}).get("content", [])

        for entry in content:
            src_pattern = entry.get("from")
            dest_pattern = entry.get("to")
            if dest_pattern is None:
                dest_pattern = ""  # let copy to root

            exclude = entry.get("exclude", [])

            src_root = self.__determine_src_root(src_pattern)
            dest_path = Path(target_root) / dest_pattern

            if isinstance(exclude, str):
                exclude = [exclude]

            # Ensure destination exists
            if dest_pattern.endswith("/"):
                dest_path.mkdir(parents=True, exist_ok=True)
            else:
                dest_path.parent.mkdir(parents=True, exist_ok=True)

            for src in base_path.glob(src_pattern):
                if any(ex in str(src) for ex in exclude):
                    continue  # Skip excluded files

                # Compute relative path based on the replaceable root
                rel_path = src.relative_to(base_path / src_root)
                target = dest_path / rel_path

                if src.is_dir():
                    shutil.copytree(src, target, dirs_exist_ok=True)
                else:
                    shutil.copy2(src, target)

    def __is_valid_folder_name(self, name):
        """Check if a string is a valid folder name (contains only valid characters)."""
        return not any(char in name for char in "*?")

    def __determine_src_root(self, src_pattern):
        """Determine the base replaceable root from the source pattern."""
        parts = Path(src_pattern).parts
        root_parts = []
        for part in parts:
            if self.__is_valid_folder_name(part):
                root_parts.append(part)
            else:
                break
        return Path(*root_parts)

    def compute_secrets(self, replacer: VariableReplacer = None):
        """
        providers = {
            'terraform': terraform_lookup,  # Lookup for terraform:: prefix
            'custom': custom_lookup,        # Lookup for custom:: prefix
        }
        """
        raw_secrets = self.deployment_data.get("hf-deploy", {}).get("secrets", {})

        return self.__compute_variables(raw_secrets, replacer)

    def compute_environment(self, replacer: VariableReplacer = None):
        """
        providers = {
            'terraform': terraform_lookup,  # Lookup for terraform:: prefix
            'custom': custom_lookup,        # Lookup for custom:: prefix
        }
        """
        raw_env = self.deployment_data.get("hf-deploy", {}).get("environment", {})

        return self.__compute_variables(raw_env, replacer)

    def __compute_variables(self, variables, replacer):
        if replacer is None:
            logger.warning("No variable provider, returning raw secrets")
            return variables

        computed = {}
        for key, value in variables.items():
            # Check if the value has any placeholders like ${prefix::KEY}
            new_value = re.sub(
                r"\${(.*?)}",
                lambda match: self.__replace_value_placeholders(
                    match.group(1), replacer
                ),
                value,
            )
            computed[key] = new_value

        return computed

    def __replace_value_placeholders(self, value, replacer):
        # Split the placeholder into prefix and key based on '::'
        parts = value.split("::", 1)

        if len(parts) == 2:
            prefix, key = parts
            return replacer.lookup(prefix, key)

        # try a default lookup
        return replacer.lookup_default(key)


class HuggingFaceAccount:
    # The repo_id is your namespace followed by the repository name: username_or_org/repo_name.
    def __init__(self, namespace: str, token: str):
        self.namespace = namespace
        self.hf_api = HfApi(token=token)

    def is_repo_deployed(self, repo_name: str):
        """Use special environment variable"""
        repo_id = self.__repo_id(repo_name)
        try:
            _ = self.hf_api.get_space_variables(repo_id)
            return True
        except RepositoryNotFoundError:
            logger.error("Space %s not found!", repo_id)

        return False

    def __dict_to_space_key_value(self, variables: dict):
        if variables is None:
            return []

        return [{"key": k, "value": v} for k, v in variables.items()]

    def __create_docker_space(self, repo_name, environment: dict, secrets: dict):
        space_variables = self.__dict_to_space_key_value(environment)
        space_secrets = self.__dict_to_space_key_value(secrets)

        repo_url = self.hf_api.create_repo(
            repo_id=self.__repo_id(repo_name),
            repo_type="space",
            space_sdk="docker",
            space_variables=space_variables,
            space_secrets=space_secrets,
            exist_ok=True,
        )

        logger.info("Repo %s URL is: %s", repo_name, repo_url)

        # api.add_space_secret(repo_id=repo_id, key="HF_TOKEN", value="hf_api_***")
        # api.add_space_variable(repo_id=repo_id, key="MODEL_REPO_ID", value="user/repo")

        # space_secrets
        # space_variables
        return repo_url

    def __update_space_content(self, repo_name, content_root_path):
        self.hf_api.upload_folder(
            folder_path=content_root_path,
            repo_id=self.__repo_id(repo_name),
            repo_type="space",
        )

    def __terminate_space(self, repo_name):
        self.hf_api.delete_repo(repo_id=self.__repo_id(repo_name), repo_type="space")

    def __repo_id(self, repo_name):
        return f"{self.namespace}/{repo_name}"

    def install(
        self,
        deployment: HuggingFaceSpaceDeployment,
        providers: list[VariableProvider] = None,
        force: bool = False,
    ):
        deployment_name = deployment.get_deployment_name()

        logger.info("Syncing space %s...", deployment_name)

        try:
            vr = VariableReplacer(providers)

            environment = deployment.compute_environment(vr)
            secrets = deployment.compute_secrets(vr)

            # check space exists
            if not self.is_repo_deployed(deployment_name):
                # 1: create repo
                self.__create_docker_space(deployment_name, environment, secrets)

                self.__prepare_deployment_and_push_to_hf(deployment)
            elif force is True:
                # re-update env and secrets
                # TODO: re-update env and secrets
                pass
            else:
                # deployed => sync files
                self.__prepare_deployment_and_push_to_hf(deployment)

            logger.info("Syncing space %s done", deployment_name)
            return True  # Success
        except Exception as e:
            logger.error("Error during space %s syncing: %s", deployment_name, e)
            logger.debug(traceback.format_exc())

    def __prepare_deployment_and_push_to_hf(
        self, deployment: HuggingFaceSpaceDeployment
    ):
        with deployment.temp_deployment_folder() as tmpdir:
            self.__update_space_content(deployment.get_deployment_name(), tmpdir)

    def destroy(self, deployment):
        """Destoy provided deployment

        Args:
            deployment (HuggingFaceSpaceDeployment): the deployment
        """
        logger.info("Destroying space %s...", deployment.get_deployment_name())
        self.__terminate_space(deployment.get_deployment_name())
        logger.info("Destroying space %s done", deployment.get_deployment_name())
