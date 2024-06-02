# SPDX-FileCopyrightText: 2024-present Sebastian Peralta <sebastian@mbodi.ai>
#
# SPDX-License-Identifier: apache-2.0
from .pypip import cli as pypip_cli

__all__ = [
  "pypip_cli",
] 

if __name__ == '__main__':
  pypip_cli()