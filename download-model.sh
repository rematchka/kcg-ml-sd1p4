#!/bin/bash

# Check if the './input/model' directory exists if not create it
if [ ! -d "./input/model" ]; then
    mkdir -p "./input/model"
fi

# Function to construct the download URL for megacmd, based on the Ubuntu version
get_download_url() {
    local version=$1
    echo "https://mega.nz/linux/repo/xUbuntu_${version}/amd64/megacmd-xUbuntu_${version}_amd64.deb"
}

# Check if the 'mega-get' command exists
if ! command -v mega-get &> /dev/null; then
    echo "megacmd not installed. Installing now"
    # Extract the Ubuntu version
    ubuntu_version=$(lsb_release -rs)

    # Get the download URL based on the Ubuntu version
    download_url=$(get_download_url "$ubuntu_version")

    # Download the package into /tmp
    package_name="/tmp/$(basename "$download_url")"
    wget "$download_url" -O "$package_name"

    # Install the downloaded package using 'apt'
    apt install "$package_name" -y

    # Clean up the downloaded package
    rm "$package_name"
fi

#
# Attempting to download v1-5-pruned-emaonly.safetensors
#
model_path="input/model/v1-5-pruned-emaonly.safetensors"

if [ -e "$model_path" ]; then
    echo "Model already exists in $model_path"
else
    mega-get --ignore-quota-warn "https://mega.nz/file/AVZnGbzL#EfXN4YINe0Wb7ukiqpCPa7THssugyCQU8pvpMpvxPAw" "$model_path"
fi


#
# Attempting to download v1-5-pruned-emaonly.ckpt
#

#model_path="input/model/v1-5-pruned-emaonly.ckpt"
#if [ -e "$model_path" ]; then
#    echo "Model already exists in $model_path"
#else
#    wget https://huggingface.co/runwayml/stable-diffusion-v1-5/resolve/main/v1-5-pruned-emaonly.ckpt -O "$model_path"
#fi