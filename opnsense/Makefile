# SARK Home LLM Gateway - OPNsense Plugin Makefile

PLUGIN_NAME=        os-sark
PLUGIN_VERSION=     2.0.0
PLUGIN_REVISION=    1
PLUGIN_COMMENT=     SARK Home LLM Gateway
PLUGIN_MAINTAINER=  sark@example.com
PLUGIN_WWW=         https://github.com/sark-project/sark
PLUGIN_DEVEL=       no

PLUGIN_DEPENDS=     python311 \
                    py311-fastapi \
                    py311-uvicorn \
                    py311-pydantic \
                    py311-httpx \
                    py311-yaml

# Menu integration
PLUGIN_MENU=        Services;SARK Home Gateway

.include "../../Mk/plugins.mk"
