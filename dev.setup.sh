#!/usr/bin/env bash
set -e

VENV_DIR=".venv"
GMSEC_DIR="${VENV_DIR}/GMSEC_API"
GMSEC_RELEASE="GMSEC_API-5.2-Ubuntu20.04_x86_64.tar.gz"
GMSEC_URL="https://github.com/nasa/GMSEC_API/releases/download/API-5.2-release/${GMSEC_RELEASE}"

echo "Creating virtual environment..."
python3 -m venv $VENV_DIR

echo "Activating virtual environment..."
source $VENV_DIR/bin/activate

echo "Installing Python dependencies..."
pip install --upgrade pip setuptools wheel
pip install -r dev.requirements.txt

echo "Downloading GMSEC API from GitHub releases..."
curl -L -o ${GMSEC_RELEASE} $GMSEC_URL

echo "Extracting GMSEC API..."
tar -xvzf ${GMSEC_RELEASE} -C ${VENV_DIR}

rm ${GMSEC_RELEASE}

echo "GMSEC extracted to ${GMSEC_DIR}"

echo "Setup complete."