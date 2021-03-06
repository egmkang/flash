from koala.conf.config import Config
import yaml

_config = Config()


def _load_config(file_name: str) -> dict:
    with open(file_name, 'r') as file:
        data = file.read()
        yaml_config = yaml.full_load(data)
        return yaml_config


def load_config(file_name: str):
    server_config = _load_config(file_name)
    if "port" in server_config:
        _config.set_port(int(server_config["port"]))
    else:
        print("需要配置port, 监听的端口")
        return
    if "ip" in server_config:
        _config.set_address(server_config["ip"])
    if "ttl" in server_config:
        _config.set_ttl(int(server_config["ttl"]))
    if "services" in server_config:
        _config.set_services(server_config["services"])
    if "log_name" in server_config:
        _config.set_log_name(server_config["log_name"])
    else:
        print("需要配置log_name, 日志名")
        return
    if "log_level" in server_config:
        _config.set_log_level(server_config["log_level"])
    if "console_log" in server_config:
        enable = bool(server_config["console_log"])
        if not enable:
            _config.disable_console_log()
    if "pd_address" in server_config:
        _config.set_pd_address(server_config["pd_address"])
    if "private_key" in server_config:
        _config.set_private_key(server_config["private_key"])
    print(server_config)
    pass
