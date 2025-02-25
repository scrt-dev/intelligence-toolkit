# Copyright (c) 2024 Microsoft Corporation. All rights reserved.
# Licensed under the MIT license. See LICENSE file in the project.
#
import pandas as pd

import app.util.session_variable as sv
from app.util.session_variable import SessionVariable


class SessionVariables:
    def __init__(self, prefix=""):
        self.username = sv.SessionVariable("")
        self.auth_reset_password_session = sv.SessionVariable("")
        self.generation_model = sv.SessionVariable("gpt-4-turbo")
        self.embedding_model = sv.SessionVariable("text-embedding-ada-002")
        self.max_embedding_size = sv.SessionVariable(500)
        self.save_cache = sv.SessionVariable(True)
