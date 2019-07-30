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
import configparser

config = configparser.RawConfigParser()
config.read('./broker.cfg')

if(config.has_option('persistence', 'local_database_path')):
    local_database_path = config.get('persistence',
                                     'local_database_path')
else:
    local_database_path = 'local_database/db.db'


db = peewee.SqliteDatabase(local_database_path)


class BaseModel(peewee.Model):

    class Meta:
        database = db


class JobState(BaseModel):

    app_id = peewee.CharField(unique=True)
    obj_serialized = peewee.BlobField()


class Plugin(BaseModel):

    name = peewee.CharField()
    source = peewee.CharField()
    plugin_source = peewee.CharField()
    module = peewee.CharField()
    component = peewee.CharField()

    def to_dict(self):
        return {
            "name": self.name,
            "source": self.source,
            "plugin_source": self.plugin_source,
            "module": self.module,
            "component": self.component
        }
