#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# ================================================== #
# This file is a part of PYGPT package               #
# Website: https://pygpt.net                         #
# GitHub:  https://github.com/szczyglis-dev/py-gpt   #
# MIT License                                        #
# Created By  : Marcin Szczygliński                  #
# Updated Date: 2024.03.16 15:00:00                  #
# ================================================== #

import os.path
import subprocess
import docker

from pygpt_net.item.ctx import CtxItem


class Runner:
    def __init__(self, plugin=None):
        """
        Cmd Runner

        :param plugin: plugin
        """
        self.plugin = plugin
        self.signals = None
        self.file_current = "_interpreter.current.py"
        self.file_input = "_interpreter.input.py"

    def send_interpreter_input(self, data: str):
        """
        Send input to subprocess

        :param data: input text
        """
        if self.signals is not None:
            self.signals.output.emit(data, "stdin")

    def send_interpreter_output(self, data: str, type: str):
        """
        Send output to interpreter

        :param data: output text
        :param type: output type
        """
        if self.signals is not None:
            self.signals.output.emit(data, type)

    def handle_result(self, stdout, stderr):
        """
        Handle result from subprocess

        :param stdout: stdout
        :param stderr: stderr
        :return: result
        """
        result = None
        if stdout:
            result = stdout.decode("utf-8")
            self.send_interpreter_output(result, "stdout")
            self.log("STDOUT: {}".format(result))
        if stderr:
            result = stderr.decode("utf-8")
            self.send_interpreter_output(result, "stderr")
            self.log("STDERR: {}".format(result))
        if result is None:
            result = "No result (STDOUT/STDERR empty)"
            self.log(result)
        return result

    def handle_result_docker(self, response) -> str:
        """
        Handle result from docker container

        :param response: response
        :return: result
        """
        result = response.decode('utf-8')
        self.send_interpreter_output(result, "stdout")
        self.log(
            "Result: {}".format(result),
            sandbox=True,
        )
        return result

    def is_sandbox(self) -> bool:
        """
        Check if sandbox is enabled

        :return: True if sandbox is enabled
        """
        return self.plugin.get_option_value('sandbox_docker')

    def get_docker(self) -> docker.client.DockerClient:
        """
        Get docker client

        :return: docker client instance
        """
        return docker.from_env()

    def get_docker_image(self) -> str:
        """
        Get docker image name

        :return: docker image
        """
        return self.plugin.get_option_value('sandbox_docker_image')

    def get_volumes(self) -> dict:
        """
        Get docker volumes

        :return: docker volumes
        """
        path = self.plugin.window.core.config.get_user_dir('data')
        mapping = {}
        mapping[path] = {
            "bind": "/data",
            "mode": "rw",
        }
        return mapping

    def run_docker(self, cmd: str):
        """
        Run docker container with command and return response

        :param cmd: command to run
        :return: response
        """
        client = self.get_docker()
        mapping = self.get_volumes()
        return client.containers.run(
            self.get_docker_image(),
            cmd,
            volumes=mapping,
            working_dir="/data",
            stdout=True,
            stderr=True,
        )

    def code_execute_file_sandbox(self, ctx: CtxItem, item: dict, request: dict) -> dict:
        """
        Execute code from file in sandbox (docker)

        :param ctx: CtxItem
        :param item: command item
        :param request: request item
        :return: response dict
        """
        path = item["params"]['path']
        msg = "Executing Python file: {}".format(path)
        self.log(msg, sandbox=True)
        cmd = self.plugin.get_option_value('python_cmd_tpl').format(
            filename=path,
        )
        # read file
        with open(path, 'r', encoding="utf-8") as file:
            code = file.read()
            self.append_input(code)
            self.send_interpreter_input(code)  # send input to interpreter

        self.log("Running command: {}".format(cmd), sandbox=True)
        response = self.run_docker(cmd)
        result = self.handle_result_docker(response)
        return {
            "request": request,
            "result": result,
            "context": result,
        }

    def code_execute_sandbox(self, ctx, item: dict, request: dict, all: bool = False) -> dict:
        """
        Execute code in sandbox (docker)

        :param ctx: CtxItem
        :param item: command item
        :param request: request item
        :param all: execute all
        :return: response dict
        """
        data = item["params"]['code']
        if not all:
            path = self.file_current
            if "path" in item["params"]:
                path = item["params"]['path']
            msg = "Saving Python file: {}".format(path)
            self.log(msg, sandbox=True)
            with open(path, 'w', encoding="utf-8") as file:
                file.write(data)
        else:
            path = self.prepare_path(self.file_input)

        self.append_input(data)
        self.send_interpreter_input(data)  # send input to interpreter

        # run code
        msg = "Executing Python code: {}".format(item["params"]['code'])
        self.log(msg, sandbox=True)
        cmd = self.plugin.get_option_value('python_cmd_tpl').format(
            filename=path,
        )
        self.log("Running command: {}".format(cmd), sandbox=True)
        response = self.run_docker(cmd)
        result = self.handle_result_docker(response)
        return {
            "request": request,
            "result": result,
            "context": result,
        }

    def sys_exec_sandbox(self, ctx: CtxItem, item: dict, request: dict) -> dict:
        """
        Execute system command in sandbox (docker)

        :param ctx: CtxItem
        :param item: command item
        :param request: request item
        :return: response dict
        """
        msg = "Executing system command: {}".format(item["params"]['command'])
        self.log(msg, sandbox=True)
        self.log(
            "Running command: {}".format(item["params"]['command']),
            sandbox=True,
        )
        response = self.run_docker(item["params"]['command'])
        result = self.handle_result_docker(response)
        return {
            "request": request,
            "result": result,
            "context": result,
        }

    def code_execute_file_host(self, ctx, item: dict, request: dict) -> dict or None:
        """
        Execute code from file on host machine

        :param ctx: CtxItem
        :param item: command item
        :param request: request item
        :return: response dict
        """
        msg = "Executing Python file: {}".format(item["params"]['path'])
        self.log(msg)
        path = self.prepare_path(item["params"]['path'])

        # check if file exists
        if not os.path.isfile(path):
            return {
                "request": request,
                "result": "File not found",
            }

        # read file
        with open(path, 'r', encoding="utf-8") as file:
            code = file.read()
            self.append_input(code)
            self.send_interpreter_input(code)  # send input to interpreter

        # run code
        cmd = self.plugin.get_option_value('python_cmd_tpl').format(filename=path)
        self.log("Running command: {}".format(cmd))
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = process.communicate()
        result = self.handle_result(stdout, stderr)
        return {
            "request": request,
            "result": result,
            "context": result,
        }

    def code_execute_host(self, ctx: CtxItem, item: dict, request: dict, all: bool = False) -> dict:
        """
        Execute code on host machine

        :param ctx: CtxItem
        :param item: command item
        :param request: request item
        :param all: execute all
        :return: response dict
        """
        # write code to file
        data = item["params"]['code']
        if not all:
            path = self.file_current
            if "path" in item["params"]:
                path = item["params"]['path']
            msg = "Saving Python file: {}".format(path)
            self.log(msg)
            path = self.prepare_path(path)
            with open(path, 'w', encoding="utf-8") as file:
                file.write(data)
        else:
            path = self.prepare_path(self.file_input)

        self.append_input(data)
        self.send_interpreter_input(data)  # send input to interpreter

        # run code
        cmd = self.plugin.get_option_value('python_cmd_tpl').format(filename=path)
        self.log("Running command: {}".format(cmd))
        process = subprocess.Popen(
            cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = process.communicate()
        result = self.handle_result(stdout, stderr)
        return {
            "request": request,
            "result": result,
            "context": result,
        }

    def append_input(self, data: str):
        """
        Append input to file

        :param data: input data
        """
        content = ""
        path = self.prepare_path(self.file_input)
        if os.path.isfile(path):
            with open(path, "r", encoding="utf-8") as f:
                content = f.read()
        with open(path, "a", encoding="utf-8") as f:
            nl = ""
            if content != "":
                nl = "\n"
            if data != "":
                f.write(nl + data)
            else:
                f.write("")

    def sys_exec_host(self, ctx: CtxItem, item: dict, request: dict) -> dict:
        """
        Execute system command on host

        :param ctx: CtxItem
        :param item: command item
        :param request: request item
        :return: response dict
        """
        msg = "Executing system command: {}".format(item["params"]['command'])
        self.log(msg)
        self.log("Running command: {}".format(item["params"]['command']))
        process = subprocess.Popen(
            item["params"]['command'],
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = process.communicate()
        result = self.handle_result(stdout, stderr)
        return {
            "request": request,
            "result": result,
            "context": result,
        }

    def is_absolute_path(self, path: str) -> bool:
        """
        Check if path is absolute

        :param path: path to check
        :return: True if absolute
        """
        return os.path.isabs(path)

    def prepare_path(self, path: str) -> str:
        """
        Prepare path

        :param path: path to prepare
        :return: prepared path
        """
        if self.is_absolute_path(path):
            return path
        else:
            if not self.is_sandbox():
                return os.path.join(
                    self.plugin.window.core.config.get_user_dir('data'),
                    path,
                )
            else:
                return path

    def error(self, err: any):
        """
        Log error message

        :param err: exception or error message
        """
        if self.signals is not None:
            self.signals.error.emit(err)

    def status(self, msg: str):
        """
        Send status message

        :param msg: status message
        """
        if self.signals is not None:
            self.signals.status.emit(msg)

    def debug(self, msg: any):
        """
        Log debug message

        :param msg: message to log
        """
        if self.signals is not None:
            self.signals.debug.emit(msg)

    def log(self, msg, sandbox: bool = False):
        """
        Log message to console

        :param msg: message to log
        :param sandbox: is sandbox mode
        """
        prefix = ''
        if sandbox:
            prefix += '[DOCKER]'
        full_msg = prefix + ' ' + str(msg)

        if self.signals is not None:
            self.signals.log.emit(full_msg)
