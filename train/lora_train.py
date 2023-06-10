import argparse
import os
import shutil
import subprocess
import sys
import zipfile
import fileinput
import toml
from accelerate.utils import write_basic_config
global COLAB

def check_dataset(dataset_dir):
    if os.path.isdir(dataset_dir):
        return dataset_dir

    if os.path.isfile(dataset_dir) and dataset_dir.endswith('.zip'):
        extracted_dir = dataset_dir[:-4]
        if os.path.isdir(extracted_dir):
            print("Dataset already extracted.")
            return extracted_dir

        with zipfile.ZipFile(dataset_dir, 'r') as zip_ref:
            zip_ref.extractall(extracted_dir)
            print("Dataset extracted successfully.")
        return extracted_dir

    raise ValueError("Invalid dataset path.")

def clone_sd_scripts(repo_dir):
    if os.path.isdir(repo_dir) and os.path.isfile(os.path.join(repo_dir, 'train_network.py')):
        print("sd-scripts repository already cloned.")
        return

    subprocess.run(["git", "clone", "git@github.com:kohya-ss/sd-scripts.git", repo_dir], check=True)
    with open(os.path.join(repo_dir, ".gitignore"), "w") as gitignore_file:
        gitignore_file.write("*\n!.gitignore\n")
    print("sd-scripts repository cloned successfully.")


def update_sd_scripts(repo_dir):
    if os.path.isfile(os.path.join(repo_dir, 'train_network.py')):
        subprocess.run(["git", "-C", repo_dir, "pull"], check=True)
        print("sd-scripts repository updated successfully.")
    else:
        print("sd-scripts repository not found. Cloning it instead.")
        clone_sd_scripts(repo_dir)

def generate_config(config_file, dataset_config_file, model_file, activation_tags, max_train_epochs, save_every_n_epochs, unet_lr, text_encoder_lr,
                    network_dim, network_alpha, batch_size, caption_extension,
                    continue_from_lora, resolution,
                    num_repeats, images_folder, project_name):

    config_dict = {
        "additional_network_arguments": {
            "unet_lr": unet_lr,
            "text_encoder_lr": text_encoder_lr,
            "network_dim": network_dim,
            "network_alpha": network_alpha,
            "network_module": "networks.lora",
            "network_args": None,
            "network_train_unet_only": True if text_encoder_lr == 0 else None,
            "network_weights": continue_from_lora if continue_from_lora else None
        },
        "optimizer_arguments": {
            "learning_rate": unet_lr,
            "lr_scheduler": "cosine_with_restarts",
            "lr_scheduler_num_cycles": 3,
            "lr_scheduler_power": None,
            "lr_warmup_steps": 0,
            "optimizer_type": "AdamW8Bit",
            "optimizer_args": None
        },
        "training_arguments": {
            "max_train_steps": None,
            "max_train_epochs": max_train_epochs,
            "save_every_n_epochs": save_every_n_epochs,
            "save_last_n_epochs": max_train_epochs,
            "train_batch_size": batch_size,
            "noise_offset": None,
            "clip_skip": 2,
            "min_snr_gamma": 5.0,
            "weighted_captions": None,
            "seed": 42,
            "max_token_length": 225,
            "xformers": True,
            "lowram": COLAB,
            "max_data_loader_n_workers": 8,
            "persistent_data_loader_workers": True,
            "save_precision": "fp16",
            "mixed_precision": "fp16",
            "output_dir": None,
            "logging_dir": None,
            "output_name": project_name,
            "log_prefix": project_name,
            "save_state": False,
            "save_last_n_epochs_state": None,
            "resume": None
        },
        "model_arguments": {
            "pretrained_model_name_or_path": model_file,
            "v2": None,
            "v_parameterization": True
        },
        "saving_arguments": {
            "save_model_as": "safetensors"
        },
        "dreambooth_arguments": {
            "prior_loss_weight": 1.0
        },
        "dataset_arguments": {
            "cache_latents": True
        }
    }

    with open(config_file, "w") as f:
        f.write(toml.dumps(config_dict))
    print(f"\nConfig saved to {config_file}")

    dataset_config_dict = {
        "general": {
            "resolution": resolution,
            "keep_tokens": keep_tokens,
            "flip_aug": False,
            "caption_extension": caption_extension,
            "enable_bucket": True,
            "bucket_reso_steps": 64,
            "bucket_no_upscale": False,
            "min_bucket_reso": 320 if resolution > 640 else 256,
            "max_bucket_reso": 1280 if resolution > 640 else 1024
        },
        "datasets": [
            {
                "subsets": [
                    {
                        "num_repeats": num_repeats,
                        "image_dir": images_folder,
                        "class_tokens": None if caption_extension else project_name
                    }
                ]
            }
        ]
    }

    with open(dataset_config_file, "w") as f:
        f.write(toml.dumps(dataset_config_dict))
    print(f"Dataset config saved to {dataset_config_file}")


def main(args):
    # Check dataset and extract if necessary
    args.images_folder = check_dataset(args.dataset)
    print(f"Dataset directory: {dataset_dir}")

    # Clone or update sd-scripts repository
    update_sd_scripts(args.repo_dir)

    # Generate config files
    generate_config(args.config_file, args.dataset_config_file, args.model_file, **vars(args))

    # Generate accelerate config if not already there
    if not os.path.exists(accelerate_config_file):
        write_basic_config(save_location=accelerate_config_file)

    os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"
    os.environ["BITSANDBYTES_NOWELCOME"] = "1"
    os.environ["SAFETENSORS_FAST_GPU"] = "1"

    # Execute training process
    print("\nStarting trainer...\n")
    os.chdir(args.repo_dir)
    subprocess.run([
        "accelerate", "launch",
        "--config_file", args.accelerate_config_file,
        "--num_cpu_threads_per_process", "1",
        "train_network.py",
        "--dataset_config", args.dataset_config_file,
        "--config_file", args.config_file
    ], check=True)

def parse_arguments():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", default="./", help="Path to the dataset directory or ZIP file.")
    parser.add_argument("--repo_dir", default="train/sd-scripts", help="Directory to clone sd-scripts repository.")
    parser.add_argument("--activation_tags", default=1, help="The number of activation tags in each txt file on the dataset.")
    parser.add_argument("--num_repeats", default=10, help="Number of times to repeat per image.")
    parser.add_argument("--max_train_epochs", default=10, help="How many epochs to train for.")
    parser.add_argument("--save_every_n_epochs", default=1, help="How frequently should we save the LoRa model.")
    parser.add_argument("--config_file", default=None, help="Path to the training configuration file.")
    parser.add_argument("--dataset_config_file", default=None, help="Path to the dataset configuration file.")
    parser.add_argument("--model_file", default="./input/model/sd-v1-4.ckpt", help="Path to the model file.")
    parser.add_argument("--log_dir", default=None, help="Path to store log files.")
    parser.add_argument("--output_dir", default=None, help="Path to store output (LoRa model) files.")
    parser.add_argument("--unet_lr", type=float, default=0.0005, help="Learning rate for the UNet model.")
    parser.add_argument("--text_encoder_lr", type=float, default=0.0001, help="Learning rate for the text encoder model.")
    parser.add_argument("--network_dim", type=int, default=512, help="Dimension of the network.")
    parser.add_argument("--network_alpha", type=int, help="Alpha value for the network.")
    parser.add_argument("--batch_size", type=int, default=3, help="Number of images to use per epoch.")
    parser.add_argument("--caption_extension", type=str, default=None, help="Do not specify if there are no captions for the image, if there are, specify the extension of the captions (eg. txt) here.")
    parser.add_argument("--resolution", type=int, default=512, help="Resolution of the images. Must be square aspect ratio (1:1).")
    parser.add_argument("--project_name", type=str, default="Test", help="Put the project name here. Will dictate the filenames of the LoRa models produced, amongst other things.")
    parser.add_argument("--continue_from_lora", default=None,
                        help="Path to the Lora file from which to continue training.")
    parser.add_argument("--accelerate_config_file", default=None,
                        help="Path to the accelerate distributed training configuration file.")
    args = parser.parse_args()
    set_defaults(args)
    return args

def set_defaults(args):
    repo_dir = os.path.abspath(args.repo_dir)
    if args.config_dir is None:
        args.config_dir = os.path.join(repo_dir, "config")

    config_dir = os.path.abspath(args.config_dir)
    # Set file defaults
    if args.config_file is None:
        args.config_file = os.path.abspath(os.path.join(config_dir, "training_config.toml"))

    if args.dataset_config_file is None:
        args.dataset_config_file = os.path.abspath(os.path.join(config_dir, "dataset_config.toml"))

    if args.accelerate_config_file is None:
        args.accelerate_config_file = os.path.abspath(os.path.join(repo_dir, "accelerate_distributed_config.toml"))

    if args.log_dir is None:
        args.log_dir = os.path.abspath(os.path.join("./output/LoRa/", args.project_name, "log"))

    if args.output_dir is None:
        args.output_dir = os.path.abspath(os.path.join("./output/LoRa/", args.project_name, "output"))

    # Make directories if they don't exist

    for dir in (args.log_dir, args.output_dir, args.repo_dir):
      if not os.path.exists(dir):
        os.makedirs(dir)

    # Patch kohya for minor stuff
    if COLAB:
        model_util_file = os.path.join(repo_dir, "library", "model_util.py")
        for line in fileinput.input(model_util_file, inplace=True):
            print(line.replace("cpu", "cuda"), end="")

    train_util_file = os.path.join(repor_dir, "library", "train_util.py")
    for line in fileinput.input(train_util_file, inplace=True):
        line = line.replace("from PIL import Image", "from PIL import Image, ImageFile\nImageFile.LOAD_TRUNCATED_IMAGES=True")
        line = line.replace("{:06d}", "{:02d}")
        print(line, end="")

    train_network_file = os.path.join(repo_dir, "train_network.py")
    for line in fileinput.input(train_network_file, inplace=True):
        line = line.replace("model_name + \".\"", "model_name + \"-{:02d}.\".format(num_train_epochs)")
        print(line, end="")


if __name__ == '__main__':
    args = parse_arguments()
    COLAB = 'google.colab' in sys.modules
    main(args)
