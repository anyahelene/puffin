export const tables = {};
export interface Audit_log {
    id : number;
    timestamp : Date;
    old_data? : object;
    new_data? : object;
    table_name : string;
    row_id : number;
    type : 'RESTRICTED'|'OPEN'|'AUTO'|'CLOSED';
}
export const audit_log_columns = [
    {
        name: "id",
        type: "int",
    },
    {
        name: "timestamp",
        type: "datetime",
    },
    {
        name: "old_data",
        type: "dict",
    },
    {
        name: "new_data",
        type: "dict",
    },
    {
        name: "table_name",
        type: "str",
    },
    {
        name: "row_id",
        type: "int",
    },
    {
        name: "type",
        type: "LogType",
    },
]
tables["audit_log"] = audit_log_columns;
export interface Id {
    id : number;
    type : string;
}
export const id_columns = [
    {
        name: "id",
        type: "int",
    },
    {
        name: "type",
        type: "str",
    },
]
tables["id"] = id_columns;
export interface Provider {
    id : number;
    name : string;
    has_external_id : boolean;
    is_primary : boolean;
}
export const provider_columns = [
    {
        name: "id",
        type: "int",
    },
    {
        name: "name",
        type: "str",
    },
    {
        name: "has_external_id",
        type: "bool",
        doc: "Whether accounts have a unique numeric id",
    },
    {
        name: "is_primary",
        type: "bool",
    },
]
tables["provider"] = provider_columns;
export interface Account {
    id : number;
    provider_id : number;
    user_id : number;
    external_id? : number;
    username : string;
    expiry_date? : Date;
    email? : string;
    fullname : string;
    note? : string;
    avatar_url? : string;
}
export const account_columns = [
    {
        name: "id",
        type: "int",
        doc: "Internal account id",
        view: {"course_user": false},
    },
    {
        name: "provider_id",
        type: "int",
        doc: "Account provider",
        view: {"course_user": false},
    },
    {
        name: "user_id",
        type: "int",
        doc: "User this account is associated with",
        view: {"course_user": false},
    },
    {
        name: "external_id",
        type: "int",
        doc: "Provider's numeric user id (if any)",
    },
    {
        name: "username",
        type: "str",
        doc: "Provider's username for this account",
    },
    {
        name: "expiry_date",
        type: "datetime",
        view: {"course_user": false},
    },
    {
        name: "email",
        type: "str",
        view: {"course_user": false},
    },
    {
        name: "fullname",
        type: "str",
        view: {"course_user": false},
    },
    {
        name: "note",
        type: "str",
        view: {"course_user": false},
    },
    {
        name: "avatar_url",
        type: "str",
        view: {"course_user": false},
    },
]
tables["account"] = account_columns;
export interface Course {
    id : number;
    external_id : number;
    name : string;
    slug : string;
    expiry_date? : Date;
}
export const course_columns = [
    {
        name: "id",
        type: "int",
        view: {"course_user": false},
    },
    {
        name: "external_id",
        type: "int",
        view: {"course_user": "course_canvas_id"},
    },
    {
        name: "name",
        type: "str",
        view: {"course_user": "course_name"},
    },
    {
        name: "slug",
        type: "str",
        view: {"course_user": "course_slug"},
    },
    {
        name: "expiry_date",
        type: "datetime",
        view: {"course_user": false},
    },
]
tables["course"] = course_columns;
export interface Group {
    id : number;
    kind : string;
    course_id : number;
    parent_id? : number;
    external_id? : string;
    name : string;
    slug : string;
    join_model : 'RESTRICTED'|'OPEN'|'AUTO'|'CLOSED';
    join_source? : string;
}
export const group_columns = [
    {
        name: "id",
        type: "int",
    },
    {
        name: "kind",
        type: "str",
    },
    {
        name: "course_id",
        type: "int",
    },
    {
        name: "parent_id",
        type: "int",
    },
    {
        name: "external_id",
        type: "str",
    },
    {
        name: "name",
        type: "str",
    },
    {
        name: "slug",
        type: "str",
    },
    {
        name: "join_model",
        type: "JoinModel",
    },
    {
        name: "join_source",
        type: "str",
        doc: "E.g. gitlab(project_id)",
    },
]
tables["group"] = group_columns;
export interface Membership {
    id : number;
    user_id : number;
    group_id : number;
    role : string;
    join_model : 'RESTRICTED'|'OPEN'|'AUTO'|'CLOSED';
}
export const membership_columns = [
    {
        name: "id",
        type: "int",
    },
    {
        name: "user_id",
        type: "int",
    },
    {
        name: "group_id",
        type: "int",
    },
    {
        name: "role",
        type: "str",
    },
    {
        name: "join_model",
        type: "JoinModel",
    },
]
tables["membership"] = membership_columns;
export interface Enrollment {
    id : number;
    user_id : number;
    course_id : number;
    role : string;
}
export const enrollment_columns = [
    {
        name: "id",
        type: "int",
        view: {"course_user": false},
    },
    {
        name: "user_id",
        type: "int",
        view: {"course_user": false},
    },
    {
        name: "course_id",
        type: "int",
    },
    {
        name: "role",
        type: "str",
        icons: {"student": "\ud83e\uddd1\u200d\ud83c\udf93", "admin": "\ud83e\uddd1\u200d\ud83d\udcbc", "": "\ud83e\uddd1\u200d\ud83c\udfeb"},
    },
]
tables["enrollment"] = enrollment_columns;
export interface User {
    id : number;
    key : string;
    lastname : string;
    firstname : string;
    email : string;
    is_admin : boolean;
    locale? : string;
    expiry_date? : Date;
    password? : string;
}
export const user_columns = [
    {
        name: "id",
        type: "int",
    },
    {
        name: "key",
        type: "str",
        hide: true,
        view: {"course_user": false},
    },
    {
        name: "lastname",
        type: "str",
    },
    {
        name: "firstname",
        type: "str",
    },
    {
        name: "email",
        type: "str",
    },
    {
        name: "is_admin",
        type: "bool",
        icons: {"true": "\ud83e\uddd1\u200d\ud83d\udcbb", "": " "},
    },
    {
        name: "locale",
        type: "str",
    },
    {
        name: "expiry_date",
        type: "datetime",
        view: {"course_user": false},
    },
]
tables["user"] = user_columns;
export interface Last_sync {
    id : number;
    obj_id : number;
    obj_type : string;
    sync_incoming? : Date;
    sync_outgoing? : Date;
}
export const last_sync_columns = [
    {
        name: "id",
        type: "int",
    },
    {
        name: "obj_id",
        type: "int",
    },
    {
        name: "obj_type",
        type: "str",
    },
    {
        name: "sync_incoming",
        type: "datetime",
    },
    {
        name: "sync_outgoing",
        type: "datetime",
    },
]
tables["last_sync"] = last_sync_columns;
export interface Oauth1token {
    id : number;
    provider_id : number;
    oauth_token : string;
    oauth_token_secret : string;
    user_id : number;
}
export const oauth1token_columns = [
    {
        name: "id",
        type: "int",
    },
    {
        name: "provider_id",
        type: "int",
    },
    {
        name: "oauth_token",
        type: "str",
    },
    {
        name: "oauth_token_secret",
        type: "str",
    },
    {
        name: "user_id",
        type: "int",
    },
]
tables["oauth1token"] = oauth1token_columns;
export interface Oauth2token {
    id : number;
    provider_id : number;
    token_type : string;
    access_token : string;
    refresh_token : string;
    expires_at : Date;
    user_id : number;
}
export const oauth2token_columns = [
    {
        name: "id",
        type: "int",
    },
    {
        name: "provider_id",
        type: "int",
    },
    {
        name: "token_type",
        type: "str",
    },
    {
        name: "access_token",
        type: "str",
    },
    {
        name: "refresh_token",
        type: "str",
    },
    {
        name: "expires_at",
        type: "datetime",
    },
    {
        name: "user_id",
        type: "int",
    },
]
tables["oauth2token"] = oauth2token_columns;
export interface Course_user {
    id : number;
    lastname? : string;
    firstname? : string;
    email? : string;
    is_admin? : boolean;
    locale? : string;
    course_id? : number;
    role? : string;
    course_canvas_id? : number;
    course_name? : string;
    course_slug? : string;
}
export const course_user_columns = [
    {
        name: "id",
        type: "int",
    },
    {
        name: "lastname",
        type: "str",
    },
    {
        name: "firstname",
        type: "str",
    },
    {
        name: "email",
        type: "str",
    },
    {
        name: "is_admin",
        type: "bool",
        icons: {"true": "\ud83e\uddd1\u200d\ud83d\udcbb", "": " "},
    },
    {
        name: "locale",
        type: "str",
    },
    {
        name: "course_id",
        type: "int",
    },
    {
        name: "role",
        type: "str",
        icons: {"student": "\ud83e\uddd1\u200d\ud83c\udf93", "admin": "\ud83e\uddd1\u200d\ud83d\udcbc", "": "\ud83e\uddd1\u200d\ud83c\udfeb"},
    },
    {
        name: "course_canvas_id",
        type: "int",
        view: {"course_user": "course_canvas_id"},
    },
    {
        name: "course_name",
        type: "str",
        view: {"course_user": "course_name"},
    },
    {
        name: "course_slug",
        type: "str",
        view: {"course_user": "course_slug"},
    },
]
tables["course_user"] = course_user_columns;
export interface User_account {
    id : number;
    canvas_id? : number;
    canvas_username? : string;
    gitlab_id? : number;
    gitlab_username? : string;
    discord_id? : number;
    discord_username? : string;
}
export const user_account_columns = [
    {
        name: "id",
        type: "int",
    },
    {
        name: "canvas_id",
        type: "int",
    },
    {
        name: "canvas_username",
        type: "str",
    },
    {
        name: "gitlab_id",
        type: "int",
    },
    {
        name: "gitlab_username",
        type: "str",
    },
    {
        name: "discord_id",
        type: "int",
    },
    {
        name: "discord_username",
        type: "str",
    },
]
tables["user_account"] = user_account_columns;
