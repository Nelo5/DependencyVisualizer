import sys
import tarfile
from io import BytesIO
import requests
import re
import base64
import subprocess


class DependencyVisualizer:
    def __init__(self):
        self.packsByProvided = {}
        self.packsAndDeps = {}
        self.result = ""
        self.setOfPacks = set()

    def start(self):
        """Инициализация данных о пакетах из APKINDEX."""
        url = "https://dl-cdn.alpinelinux.org/alpine/v3.20/main/x86_64/APKINDEX.tar.gz"
        try:
            response = requests.get(url, stream=True)
            response.raise_for_status()
        except requests.RequestException as e:
            print(f"Error fetching APKINDEX: {e}")
            sys.exit(1)

        try:
            with tarfile.open(fileobj=BytesIO(response.content), mode="r:gz") as tar_file:
                apkindex = tar_file.extractfile("APKINDEX")
                if not apkindex:
                    raise ValueError("APKINDEX file not found in the archive.")

                package = 4 * [""]
                for line in apkindex:
                    if len(line) == 1:
                        if package[0] == ("boost-dev" or "zfs-virt"):
                            package[0] += f'={package[1]}'
                        self.packsAndDeps[package[0]] = package[2]
                        if package[3]:
                            for providedPart in package[3]:
                                self.packsByProvided[re.split(">=|=|>", providedPart)[0]] = package[0]
                        package = 4 * [""]
                    elif line.decode()[0] == "P":
                        package[0] = line.decode()[2:-1]
                    elif line.decode()[0] == "V":
                        package[1] = line.decode()[2:-1]
                    elif line.decode()[0] == "D":
                        package[2] = line.decode()[2:-1].split()
                    elif line.decode()[0] == "p":
                        package[3] = line.decode()[2:-1].split()
        except (tarfile.TarError, ValueError) as e:
            print(f"Error processing APKINDEX file: {e}")
            sys.exit(1)

        # Добавление дополнительных предоставляемых пакетов
        self.packsByProvided["/bin/sh"] = "busybox-binsh"
        self.packsByProvided["icu-data"] = "icu-data-en"
        self.packsByProvided["dnsmasq"] = "dnsmasq"
        self.packsByProvided["openssh-client"] = "openssh-client-default"
        self.packsByProvided["cmd:ssh"] = "openssh-client-default"

    def addDepends(self, name):
        """Рекурсивное добавление зависимостей для пакета."""
        try:
            currDeps = set()
            if self.packsAndDeps[name]:
                for dep in self.packsAndDeps[name]:
                    curdep = re.split(">=|=|>", dep)[0]
                    if curdep in self.packsAndDeps:
                        currDeps.add(curdep)
                    elif curdep in self.packsByProvided:
                        currDeps.add(self.packsByProvided[curdep])

            for dep in currDeps:
                self.result += f"{name} --> {dep}\n"

            for dep in currDeps:
                if dep not in self.setOfPacks:
                    self.setOfPacks.add(dep)
                    self.addDepends(dep)
        except KeyError as e:
            print(f"Dependency error: Package '{name}' not found. {e}")
        except Exception as e:
            print(f"Error processing dependencies for '{name}': {e}")

    def get_graph(self, name):
        """Генерация графа зависимостей и возврат ссылки на изображение."""
        try:
            self.setOfPacks = set()
            self.result = "graph\n"
            if len(self.packsAndDeps[name]) == 0:
                self.result += name
            else:
                self.addDepends(name)
            graph = self.result
            graphbytes = graph.encode("utf-8")
            base64_bytes = base64.urlsafe_b64encode(graphbytes)
            base64_string = base64_bytes.decode("ascii")
            link = f"https://mermaid.ink/img/{base64_string}"
            return link
        except Exception as e:
            print(f"Error generating graph for '{name}': {e}")
            sys.exit(1)

    def display_graph(self, name, script_path):
        """Загрузка изображения и вызов Bash-скрипта."""
        try:
            graph_url = self.get_graph(name)
            response = requests.get(graph_url, stream=True)
            response.raise_for_status()

            # Сохранение изображения во временный файл
            temp_filename = "downloaded_image.png"
            with open(temp_filename, "wb") as img_file:
                img_file.write(response.content)

            # Запуск Bash-скрипта
            subprocess.run(["bash", script_path, temp_filename], check=True)
        except requests.RequestException as e:
            print(f"Error fetching graph image: {e}")
        except subprocess.CalledProcessError as e:
            print(f"Error executing Bash script: {e}")
        except Exception as e:
            print(f"Error in display_graph: {e}")


# Основной код
if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 script.py <package_name> <bash_script_path>")
        sys.exit(1)

    package_name = sys.argv[1]
    bash_script_path = sys.argv[2]

    try:
        grapher = DependencyVisualizer()
        grapher.start()
        grapher.display_graph(package_name, bash_script_path)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)
