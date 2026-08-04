import subprocess


def gpu_info():

    try:

        subprocess.run(["nvidia-smi"])

    except:

        print("GPU not detected")
