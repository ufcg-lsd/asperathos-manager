# Copyright (c) 2019 UFCG-LSD.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# -*- coding: utf_8 -*-
import peewee
from broker.service import api

db = peewee.SqliteDatabase(api.local_database_path)


class JobState(peewee.Model):

    app_id = peewee.CharField(unique=True)
    obj_serialized = peewee.BlobField()

    class Meta:
        database = db
