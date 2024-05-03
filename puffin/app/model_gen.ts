import { isEqual } from "lodash-es";export const tables = {};
export class _AuditLog {
    revision : number;
    id : number;
    timestamp : Date;
    old_data? : Record<string,any> = {};
    new_data? : Record<string,any> = {};
    table_name : string;
    row_id : number;
    type : 'UPDATE'|'INSERT'|'DELETE';
    constructor(jsonData:Record<string,any>, revision=0) {
        this.id = jsonData.id;
        this.update(jsonData, revision);
    }

    _log: [string, string][] = [];
    log(level: string, msg?: string) {
        if (msg !== undefined) this._log.unshift([level, msg]);
        else this._log.unshift(['info', level]);
    }
    clear_log() {
        this._log = [];
    }
    update(jsonData:Record<string,any>, revision=0) : boolean {
        if(this.id !== jsonData.id) throw new Error("Data doesn't match ID");
        this.revision = revision;
        let changed = false;
        if(this.timestamp !== jsonData.timestamp) {
            changed = true;
            this.timestamp = jsonData.timestamp;
        }
        if(!isEqual(this.old_data, jsonData.old_data)) {
            changed = true;
            this.old_data = {...jsonData.old_data};
        }
        if(!isEqual(this.new_data, jsonData.new_data)) {
            changed = true;
            this.new_data = {...jsonData.new_data};
        }
        if(this.table_name !== jsonData.table_name) {
            changed = true;
            this.table_name = jsonData.table_name;
        }
        if(this.row_id !== jsonData.row_id) {
            changed = true;
            this.row_id = jsonData.row_id;
        }
        if(this.type !== jsonData.type) {
            changed = true;
            this.type = jsonData.type;
        }
        return changed;
    }
}
export const AuditLog_columns = [
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
tables["AuditLog"] = AuditLog_columns;
export class _Id {
    revision : number;
    id : number;
    type : string;
    constructor(jsonData:Record<string,any>, revision=0) {
        this.id = jsonData.id;
        this.type = jsonData.type;
        this.update(jsonData, revision);
    }

    _log: [string, string][] = [];
    log(level: string, msg?: string) {
        if (msg !== undefined) this._log.unshift([level, msg]);
        else this._log.unshift(['info', level]);
    }
    clear_log() {
        this._log = [];
    }
    update(jsonData:Record<string,any>, revision=0) : boolean {
        if(this.id !== jsonData.id) throw new Error("Data doesn't match ID");
        this.revision = revision;
        let changed = false;
        return changed;
    }
}
export const Id_columns = [
    {
        name: "id",
        type: "int",
    },
    {
        name: "type",
        type: "str",
        immutable: true,
    },
]
tables["Id"] = Id_columns;
export class _Account {
    revision : number;
    id : number;
    provider_name : string;
    user_id : number;
    external_id? : number;
    username : string;
    expiry_date? : Date;
    email? : string;
    fullname : string;
    note? : string;
    email_verified : boolean;
    last_login? : Date;
    avatar_url? : string;
    constructor(jsonData:Record<string,any>, revision=0) {
        this.id = jsonData.id;
        this.user_id = jsonData.user_id;
        this.update(jsonData, revision);
    }

    _log: [string, string][] = [];
    log(level: string, msg?: string) {
        if (msg !== undefined) this._log.unshift([level, msg]);
        else this._log.unshift(['info', level]);
    }
    clear_log() {
        this._log = [];
    }
    update(jsonData:Record<string,any>, revision=0) : boolean {
        if(this.id !== jsonData.id) throw new Error("Data doesn't match ID");
        this.revision = revision;
        let changed = false;
        if(this.provider_name !== jsonData.provider_name) {
            changed = true;
            this.provider_name = jsonData.provider_name;
        }
        if(this.external_id !== jsonData.external_id) {
            changed = true;
            this.external_id = jsonData.external_id;
        }
        if(this.username !== jsonData.username) {
            changed = true;
            this.username = jsonData.username;
        }
        if(this.expiry_date !== jsonData.expiry_date) {
            changed = true;
            this.expiry_date = jsonData.expiry_date;
        }
        if(this.email !== jsonData.email) {
            changed = true;
            this.email = jsonData.email;
        }
        if(this.fullname !== jsonData.fullname) {
            changed = true;
            this.fullname = jsonData.fullname;
        }
        if(this.note !== jsonData.note) {
            changed = true;
            this.note = jsonData.note;
        }
        if(this.email_verified !== jsonData.email_verified) {
            changed = true;
            this.email_verified = jsonData.email_verified;
        }
        if(this.last_login !== jsonData.last_login) {
            changed = true;
            this.last_login = jsonData.last_login;
        }
        if(this.avatar_url !== jsonData.avatar_url) {
            changed = true;
            this.avatar_url = jsonData.avatar_url;
        }
        return changed;
    }
}
export const Account_columns = [
    {
        name: "id",
        type: "int",
        doc: "Internal account id",
        view: {"course_user": false},
    },
    {
        name: "provider_name",
        type: "str",
        doc: "Account provider",
        view: {"course_user": false},
    },
    {
        name: "user_id",
        type: "int",
        doc: "User this account is associated with",
        view: {"course_user": false},
        immutable: true,
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
        name: "email_verified",
        type: "bool",
    },
    {
        name: "last_login",
        type: "datetime",
        view: {"course_user": false},
    },
    {
        name: "avatar_url",
        type: "str",
        view: {"course_user": false},
    },
]
tables["Account"] = Account_columns;
export class _Course {
    revision : number;
    id : number;
    external_id : number;
    name : string;
    slug : string;
    expiry_date? : Date;
    json_data : Record<string,any> = {};
    constructor(jsonData:Record<string,any>, revision=0) {
        this.id = jsonData.id;
        this.external_id = jsonData.external_id;
        this.update(jsonData, revision);
    }

    _log: [string, string][] = [];
    log(level: string, msg?: string) {
        if (msg !== undefined) this._log.unshift([level, msg]);
        else this._log.unshift(['info', level]);
    }
    clear_log() {
        this._log = [];
    }
    update(jsonData:Record<string,any>, revision=0) : boolean {
        if(this.id !== jsonData.id) throw new Error("Data doesn't match ID");
        this.revision = revision;
        let changed = false;
        if(this.name !== jsonData.name) {
            changed = true;
            this.name = jsonData.name;
        }
        if(this.slug !== jsonData.slug) {
            changed = true;
            this.slug = jsonData.slug;
        }
        if(this.expiry_date !== jsonData.expiry_date) {
            changed = true;
            this.expiry_date = jsonData.expiry_date;
        }
        if(!isEqual(this.json_data, jsonData.json_data)) {
            changed = true;
            this.json_data = {...jsonData.json_data};
        }
        return changed;
    }
}
export const Course_columns = [
    {
        name: "id",
        type: "int",
        view: {"course_user": false},
    },
    {
        name: "external_id",
        type: "int",
        view: {"course_user": "course_canvas_id"},
        immutable: true,
        form: "canvas_course",
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
        form: {"slugify": "name"},
    },
    {
        name: "expiry_date",
        type: "datetime",
        view: {"course_user": false},
    },
    {
        name: "json_data",
        type: "dict",
        view: {"course_user": false, "full_user": false},
    },
]
tables["Course"] = Course_columns;
export class _Group {
    revision : number;
    id : number;
    kind : string;
    course_id : number;
    parent_id? : number;
    external_id? : string;
    name : string;
    slug : string;
    join_model : 'RESTRICTED'|'OPEN'|'AUTO'|'CLOSED';
    join_source? : string;
    json_data : Record<string,any> = {};
    constructor(jsonData:Record<string,any>, revision=0) {
        this.id = jsonData.id;
        this.course_id = jsonData.course_id;
        this.update(jsonData, revision);
    }

    _log: [string, string][] = [];
    log(level: string, msg?: string) {
        if (msg !== undefined) this._log.unshift([level, msg]);
        else this._log.unshift(['info', level]);
    }
    clear_log() {
        this._log = [];
    }
    update(jsonData:Record<string,any>, revision=0) : boolean {
        if(this.id !== jsonData.id) throw new Error("Data doesn't match ID");
        this.revision = revision;
        let changed = false;
        if(this.kind !== jsonData.kind) {
            changed = true;
            this.kind = jsonData.kind;
        }
        if(this.parent_id !== jsonData.parent_id) {
            changed = true;
            this.parent_id = jsonData.parent_id;
        }
        if(this.external_id !== jsonData.external_id) {
            changed = true;
            this.external_id = jsonData.external_id;
        }
        if(this.name !== jsonData.name) {
            changed = true;
            this.name = jsonData.name;
        }
        if(this.slug !== jsonData.slug) {
            changed = true;
            this.slug = jsonData.slug;
        }
        if(this.join_model !== jsonData.join_model) {
            changed = true;
            this.join_model = jsonData.join_model;
        }
        if(this.join_source !== jsonData.join_source) {
            changed = true;
            this.join_source = jsonData.join_source;
        }
        if(!isEqual(this.json_data, jsonData.json_data)) {
            changed = true;
            this.json_data = {...jsonData.json_data};
        }
        return changed;
    }
}
export const Group_columns = [
    {
        name: "id",
        type: "int",
    },
    {
        name: "kind",
        type: "str",
        form: {"select": "group_kind"},
    },
    {
        name: "course_id",
        type: "int",
        immutable: true,
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
        access: {"write": "member"},
    },
    {
        name: "slug",
        type: "group.slug",
        form: {"slugify": "name"},
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
    {
        name: "json_data",
        type: "dict",
    },
]
tables["Group"] = Group_columns;
export class _Membership {
    revision : number;
    id : number;
    user_id : number;
    group_id : number;
    role : string;
    join_model : 'RESTRICTED'|'OPEN'|'AUTO'|'CLOSED';
    constructor(jsonData:Record<string,any>, revision=0) {
        this.id = jsonData.id;
        this.user_id = jsonData.user_id;
        this.group_id = jsonData.group_id;
        this.update(jsonData, revision);
    }

    _log: [string, string][] = [];
    log(level: string, msg?: string) {
        if (msg !== undefined) this._log.unshift([level, msg]);
        else this._log.unshift(['info', level]);
    }
    clear_log() {
        this._log = [];
    }
    update(jsonData:Record<string,any>, revision=0) : boolean {
        if(this.id !== jsonData.id) throw new Error("Data doesn't match ID");
        this.revision = revision;
        let changed = false;
        if(this.role !== jsonData.role) {
            changed = true;
            this.role = jsonData.role;
        }
        if(this.join_model !== jsonData.join_model) {
            changed = true;
            this.join_model = jsonData.join_model;
        }
        return changed;
    }
}
export const Membership_columns = [
    {
        name: "id",
        type: "int",
    },
    {
        name: "user_id",
        type: "int",
        immutable: true,
        access: {"read": "peer"},
    },
    {
        name: "group_id",
        type: "int",
        immutable: true,
    },
    {
        name: "role",
        type: "str",
        icons: {"student": "\ud83e\uddd1\u200d\ud83c\udf93", "ta": "\ud83e\uddd1\u200d\ud83d\udcbb", "teacher": "\ud83e\uddd1\u200d\ud83c\udfeb", "admin": "\ud83e\uddd1\u200d\ud83d\udcbc", "": "\ud83e\udd37"},
    },
    {
        name: "join_model",
        type: "JoinModel",
    },
]
tables["Membership"] = Membership_columns;
export class _Enrollment {
    revision : number;
    id : number;
    user_id : number;
    course_id : number;
    role : string;
    constructor(jsonData:Record<string,any>, revision=0) {
        this.id = jsonData.id;
        this.user_id = jsonData.user_id;
        this.course_id = jsonData.course_id;
        this.update(jsonData, revision);
    }

    _log: [string, string][] = [];
    log(level: string, msg?: string) {
        if (msg !== undefined) this._log.unshift([level, msg]);
        else this._log.unshift(['info', level]);
    }
    clear_log() {
        this._log = [];
    }
    update(jsonData:Record<string,any>, revision=0) : boolean {
        if(this.id !== jsonData.id) throw new Error("Data doesn't match ID");
        this.revision = revision;
        let changed = false;
        if(this.role !== jsonData.role) {
            changed = true;
            this.role = jsonData.role;
        }
        return changed;
    }
}
export const Enrollment_columns = [
    {
        name: "id",
        type: "int",
        view: {"course_user": false},
    },
    {
        name: "user_id",
        type: "int",
        view: {"course_user": false},
        immutable: true,
        access: {"read": "peer"},
    },
    {
        name: "course_id",
        type: "int",
        immutable: true,
    },
    {
        name: "role",
        type: "str",
        icons: {"student": "\ud83e\uddd1\u200d\ud83c\udf93", "ta": "\ud83e\uddd1\u200d\ud83d\udcbb", "teacher": "\ud83e\uddd1\u200d\ud83c\udfeb", "admin": "\ud83e\uddd1\u200d\ud83d\udcbc", "": "\ud83e\udd37"},
        access: {"write": "admin", "read": "peer"},
    },
]
tables["Enrollment"] = Enrollment_columns;
export class _User {
    revision : number;
    id : number;
    key : string;
    lastname : string;
    firstname : string;
    email : string;
    is_admin : boolean;
    locale? : string;
    expiry_date? : Date;
    constructor(jsonData:Record<string,any>, revision=0) {
        this.id = jsonData.id;
        this.update(jsonData, revision);
    }

    _log: [string, string][] = [];
    log(level: string, msg?: string) {
        if (msg !== undefined) this._log.unshift([level, msg]);
        else this._log.unshift(['info', level]);
    }
    clear_log() {
        this._log = [];
    }
    update(jsonData:Record<string,any>, revision=0) : boolean {
        if(this.id !== jsonData.id) throw new Error("Data doesn't match ID");
        this.revision = revision;
        let changed = false;
        if(this.key !== jsonData.key) {
            changed = true;
            this.key = jsonData.key;
        }
        if(this.lastname !== jsonData.lastname) {
            changed = true;
            this.lastname = jsonData.lastname;
        }
        if(this.firstname !== jsonData.firstname) {
            changed = true;
            this.firstname = jsonData.firstname;
        }
        if(this.email !== jsonData.email) {
            changed = true;
            this.email = jsonData.email;
        }
        if(this.is_admin !== jsonData.is_admin) {
            changed = true;
            this.is_admin = jsonData.is_admin;
        }
        if(this.locale !== jsonData.locale) {
            changed = true;
            this.locale = jsonData.locale;
        }
        if(this.expiry_date !== jsonData.expiry_date) {
            changed = true;
            this.expiry_date = jsonData.expiry_date;
        }
        return changed;
    }
}
export const User_columns = [
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
        hide: true,
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
tables["User"] = User_columns;
export class _Assignment {
    revision : number;
    id : number;
    name : string;
    slug : string;
    description? : string;
    category : string;
    course_id : number;
    assignment_model : 'GITLAB_STUDENT_FORK'|'GITLAB_GROUP_FORK'|'GITLAB_GROUP_PROJECT'|'GITLAB_STUDENT_PROJECT';
    gitlab_id? : number;
    gitlab_root_id? : number;
    gitlab_test_id? : number;
    canvas_id? : string;
    release_date? : Date;
    due_date? : Date;
    grade_by_date? : Date;
    json_data : Record<string,any> = {};
    constructor(jsonData:Record<string,any>, revision=0) {
        this.id = jsonData.id;
        this.update(jsonData, revision);
    }

    _log: [string, string][] = [];
    log(level: string, msg?: string) {
        if (msg !== undefined) this._log.unshift([level, msg]);
        else this._log.unshift(['info', level]);
    }
    clear_log() {
        this._log = [];
    }
    update(jsonData:Record<string,any>, revision=0) : boolean {
        if(this.id !== jsonData.id) throw new Error("Data doesn't match ID");
        this.revision = revision;
        let changed = false;
        if(this.name !== jsonData.name) {
            changed = true;
            this.name = jsonData.name;
        }
        if(this.slug !== jsonData.slug) {
            changed = true;
            this.slug = jsonData.slug;
        }
        if(this.description !== jsonData.description) {
            changed = true;
            this.description = jsonData.description;
        }
        if(this.category !== jsonData.category) {
            changed = true;
            this.category = jsonData.category;
        }
        if(this.course_id !== jsonData.course_id) {
            changed = true;
            this.course_id = jsonData.course_id;
        }
        if(this.assignment_model !== jsonData.assignment_model) {
            changed = true;
            this.assignment_model = jsonData.assignment_model;
        }
        if(this.gitlab_id !== jsonData.gitlab_id) {
            changed = true;
            this.gitlab_id = jsonData.gitlab_id;
        }
        if(this.gitlab_root_id !== jsonData.gitlab_root_id) {
            changed = true;
            this.gitlab_root_id = jsonData.gitlab_root_id;
        }
        if(this.gitlab_test_id !== jsonData.gitlab_test_id) {
            changed = true;
            this.gitlab_test_id = jsonData.gitlab_test_id;
        }
        if(this.canvas_id !== jsonData.canvas_id) {
            changed = true;
            this.canvas_id = jsonData.canvas_id;
        }
        if(this.release_date !== jsonData.release_date) {
            changed = true;
            this.release_date = jsonData.release_date;
        }
        if(this.due_date !== jsonData.due_date) {
            changed = true;
            this.due_date = jsonData.due_date;
        }
        if(this.grade_by_date !== jsonData.grade_by_date) {
            changed = true;
            this.grade_by_date = jsonData.grade_by_date;
        }
        if(!isEqual(this.json_data, jsonData.json_data)) {
            changed = true;
            this.json_data = {...jsonData.json_data};
        }
        return changed;
    }
}
export const Assignment_columns = [
    {
        name: "id",
        type: "int",
    },
    {
        name: "name",
        type: "str",
        form: true,
    },
    {
        name: "slug",
        type: "str",
        form: {"slugify": "name"},
    },
    {
        name: "description",
        type: "str",
        form: "textarea",
    },
    {
        name: "category",
        type: "str",
        form: {"select": "category"},
    },
    {
        name: "course_id",
        type: "int",
    },
    {
        name: "assignment_model",
        type: "AssignmentModel",
        form: {"select": "assignment_model"},
    },
    {
        name: "gitlab_id",
        type: "int",
        doc: "GitLab source project (with solution / all tests)",
        form: "gitlab:project",
    },
    {
        name: "gitlab_root_id",
        type: "int",
        doc: "GitLab project to be forked to students",
        form: "gitlab:root_project",
    },
    {
        name: "gitlab_test_id",
        type: "int",
        doc: "GitLab project with extra (non-student visible) tests",
        form: "gitlab:test_project",
    },
    {
        name: "canvas_id",
        type: "str",
        doc: "Corresponding assignment in Canvas",
        form: "canvas:assignment",
    },
    {
        name: "release_date",
        type: "datetime",
        doc: "When the assignment should be published",
        form: {"default": "datetime.now()"},
    },
    {
        name: "due_date",
        type: "datetime",
        doc: "Default due date",
        form: true,
    },
    {
        name: "grade_by_date",
        type: "datetime",
        doc: "Date when grading is due",
        form: true,
    },
    {
        name: "json_data",
        type: "dict",
    },
]
tables["Assignment"] = Assignment_columns;
export class _Grader {
    revision : number;
    id : number;
    grader_id : number;
    student_assignment_id : number;
    grade_by_date? : Date;
    graded_date? : Date;
    grade_points? : number;
    grade_report? : string;
    constructor(jsonData:Record<string,any>, revision=0) {
        this.id = jsonData.id;
        this.update(jsonData, revision);
    }

    _log: [string, string][] = [];
    log(level: string, msg?: string) {
        if (msg !== undefined) this._log.unshift([level, msg]);
        else this._log.unshift(['info', level]);
    }
    clear_log() {
        this._log = [];
    }
    update(jsonData:Record<string,any>, revision=0) : boolean {
        if(this.id !== jsonData.id) throw new Error("Data doesn't match ID");
        this.revision = revision;
        let changed = false;
        if(this.grader_id !== jsonData.grader_id) {
            changed = true;
            this.grader_id = jsonData.grader_id;
        }
        if(this.student_assignment_id !== jsonData.student_assignment_id) {
            changed = true;
            this.student_assignment_id = jsonData.student_assignment_id;
        }
        if(this.grade_by_date !== jsonData.grade_by_date) {
            changed = true;
            this.grade_by_date = jsonData.grade_by_date;
        }
        if(this.graded_date !== jsonData.graded_date) {
            changed = true;
            this.graded_date = jsonData.graded_date;
        }
        if(this.grade_points !== jsonData.grade_points) {
            changed = true;
            this.grade_points = jsonData.grade_points;
        }
        if(this.grade_report !== jsonData.grade_report) {
            changed = true;
            this.grade_report = jsonData.grade_report;
        }
        return changed;
    }
}
export const Grader_columns = [
    {
        name: "id",
        type: "int",
    },
    {
        name: "grader_id",
        type: "int",
    },
    {
        name: "student_assignment_id",
        type: "int",
    },
    {
        name: "grade_by_date",
        type: "datetime",
    },
    {
        name: "graded_date",
        type: "datetime",
    },
    {
        name: "grade_points",
        type: "int",
    },
    {
        name: "grade_report",
        type: "str",
    },
]
tables["Grader"] = Grader_columns;
export class _StudentAssignment {
    revision : number;
    id : number;
    user_id : number;
    assignment_id : number;
    project_id? : number;
    canvas_id? : string;
    due_date? : Date;
    json_data : Record<string,any> = {};
    constructor(jsonData:Record<string,any>, revision=0) {
        this.id = jsonData.id;
        this.update(jsonData, revision);
    }

    _log: [string, string][] = [];
    log(level: string, msg?: string) {
        if (msg !== undefined) this._log.unshift([level, msg]);
        else this._log.unshift(['info', level]);
    }
    clear_log() {
        this._log = [];
    }
    update(jsonData:Record<string,any>, revision=0) : boolean {
        if(this.id !== jsonData.id) throw new Error("Data doesn't match ID");
        this.revision = revision;
        let changed = false;
        if(this.user_id !== jsonData.user_id) {
            changed = true;
            this.user_id = jsonData.user_id;
        }
        if(this.assignment_id !== jsonData.assignment_id) {
            changed = true;
            this.assignment_id = jsonData.assignment_id;
        }
        if(this.project_id !== jsonData.project_id) {
            changed = true;
            this.project_id = jsonData.project_id;
        }
        if(this.canvas_id !== jsonData.canvas_id) {
            changed = true;
            this.canvas_id = jsonData.canvas_id;
        }
        if(this.due_date !== jsonData.due_date) {
            changed = true;
            this.due_date = jsonData.due_date;
        }
        if(!isEqual(this.json_data, jsonData.json_data)) {
            changed = true;
            this.json_data = {...jsonData.json_data};
        }
        return changed;
    }
}
export const StudentAssignment_columns = [
    {
        name: "id",
        type: "int",
    },
    {
        name: "user_id",
        type: "int",
    },
    {
        name: "assignment_id",
        type: "int",
    },
    {
        name: "project_id",
        type: "int",
    },
    {
        name: "canvas_id",
        type: "str",
    },
    {
        name: "due_date",
        type: "datetime",
    },
    {
        name: "json_data",
        type: "dict",
    },
]
tables["StudentAssignment"] = StudentAssignment_columns;
export class _Project {
    revision : number;
    id : number;
    name : string;
    slug : string;
    namespace_slug : string;
    description? : string;
    course_id : number;
    owner_id : number;
    owner_kind : string;
    gitlab_id? : string;
    submitted_ref? : string;
    json_data : Record<string,any> = {};
    constructor(jsonData:Record<string,any>, revision=0) {
        this.id = jsonData.id;
        this.update(jsonData, revision);
    }

    _log: [string, string][] = [];
    log(level: string, msg?: string) {
        if (msg !== undefined) this._log.unshift([level, msg]);
        else this._log.unshift(['info', level]);
    }
    clear_log() {
        this._log = [];
    }
    update(jsonData:Record<string,any>, revision=0) : boolean {
        if(this.id !== jsonData.id) throw new Error("Data doesn't match ID");
        this.revision = revision;
        let changed = false;
        if(this.name !== jsonData.name) {
            changed = true;
            this.name = jsonData.name;
        }
        if(this.slug !== jsonData.slug) {
            changed = true;
            this.slug = jsonData.slug;
        }
        if(this.namespace_slug !== jsonData.namespace_slug) {
            changed = true;
            this.namespace_slug = jsonData.namespace_slug;
        }
        if(this.description !== jsonData.description) {
            changed = true;
            this.description = jsonData.description;
        }
        if(this.course_id !== jsonData.course_id) {
            changed = true;
            this.course_id = jsonData.course_id;
        }
        if(this.owner_id !== jsonData.owner_id) {
            changed = true;
            this.owner_id = jsonData.owner_id;
        }
        if(this.owner_kind !== jsonData.owner_kind) {
            changed = true;
            this.owner_kind = jsonData.owner_kind;
        }
        if(this.gitlab_id !== jsonData.gitlab_id) {
            changed = true;
            this.gitlab_id = jsonData.gitlab_id;
        }
        if(this.submitted_ref !== jsonData.submitted_ref) {
            changed = true;
            this.submitted_ref = jsonData.submitted_ref;
        }
        if(!isEqual(this.json_data, jsonData.json_data)) {
            changed = true;
            this.json_data = {...jsonData.json_data};
        }
        return changed;
    }
}
export const Project_columns = [
    {
        name: "id",
        type: "int",
    },
    {
        name: "name",
        type: "str",
        form: true,
        sync: true,
    },
    {
        name: "slug",
        type: "str",
        form: {"slugify": "name"},
        sync: "immutable",
    },
    {
        name: "namespace_slug",
        type: "str",
        form: false,
        sync: "immutable",
    },
    {
        name: "description",
        type: "str",
        form: "textarea",
        sync: true,
    },
    {
        name: "course_id",
        type: "int",
    },
    {
        name: "owner_id",
        type: "int",
        doc: "A user, group or course id",
    },
    {
        name: "owner_kind",
        type: "str",
    },
    {
        name: "gitlab_id",
        type: "str",
    },
    {
        name: "submitted_ref",
        type: "str",
        doc: "Identifies actual submission (a tag, branch or commit id)",
    },
    {
        name: "json_data",
        type: "dict",
    },
]
tables["Project"] = Project_columns;
export class _ProjectTestRun {
    revision : number;
    id : number;
    project_id : number;
    timestamp : Date;
    compile_passed : boolean;
    test_passed : boolean;
    result_points : number;
    result_text? : string;
    result_url? : string;
    constructor(jsonData:Record<string,any>, revision=0) {
        this.id = jsonData.id;
        this.update(jsonData, revision);
    }

    _log: [string, string][] = [];
    log(level: string, msg?: string) {
        if (msg !== undefined) this._log.unshift([level, msg]);
        else this._log.unshift(['info', level]);
    }
    clear_log() {
        this._log = [];
    }
    update(jsonData:Record<string,any>, revision=0) : boolean {
        if(this.id !== jsonData.id) throw new Error("Data doesn't match ID");
        this.revision = revision;
        let changed = false;
        if(this.project_id !== jsonData.project_id) {
            changed = true;
            this.project_id = jsonData.project_id;
        }
        if(this.timestamp !== jsonData.timestamp) {
            changed = true;
            this.timestamp = jsonData.timestamp;
        }
        if(this.compile_passed !== jsonData.compile_passed) {
            changed = true;
            this.compile_passed = jsonData.compile_passed;
        }
        if(this.test_passed !== jsonData.test_passed) {
            changed = true;
            this.test_passed = jsonData.test_passed;
        }
        if(this.result_points !== jsonData.result_points) {
            changed = true;
            this.result_points = jsonData.result_points;
        }
        if(this.result_text !== jsonData.result_text) {
            changed = true;
            this.result_text = jsonData.result_text;
        }
        if(this.result_url !== jsonData.result_url) {
            changed = true;
            this.result_url = jsonData.result_url;
        }
        return changed;
    }
}
export const ProjectTestRun_columns = [
    {
        name: "id",
        type: "int",
    },
    {
        name: "project_id",
        type: "int",
    },
    {
        name: "timestamp",
        type: "datetime",
    },
    {
        name: "compile_passed",
        type: "bool",
    },
    {
        name: "test_passed",
        type: "bool",
    },
    {
        name: "result_points",
        type: "int",
    },
    {
        name: "result_text",
        type: "str",
    },
    {
        name: "result_url",
        type: "str",
    },
]
tables["ProjectTestRun"] = ProjectTestRun_columns;
export class _LastSync {
    revision : number;
    id : number;
    obj_id : number;
    obj_type : string;
    sync_incoming? : Date;
    sync_outgoing? : Date;
    constructor(jsonData:Record<string,any>, revision=0) {
        this.id = jsonData.id;
        this.update(jsonData, revision);
    }

    _log: [string, string][] = [];
    log(level: string, msg?: string) {
        if (msg !== undefined) this._log.unshift([level, msg]);
        else this._log.unshift(['info', level]);
    }
    clear_log() {
        this._log = [];
    }
    update(jsonData:Record<string,any>, revision=0) : boolean {
        if(this.id !== jsonData.id) throw new Error("Data doesn't match ID");
        this.revision = revision;
        let changed = false;
        if(this.obj_id !== jsonData.obj_id) {
            changed = true;
            this.obj_id = jsonData.obj_id;
        }
        if(this.obj_type !== jsonData.obj_type) {
            changed = true;
            this.obj_type = jsonData.obj_type;
        }
        if(this.sync_incoming !== jsonData.sync_incoming) {
            changed = true;
            this.sync_incoming = jsonData.sync_incoming;
        }
        if(this.sync_outgoing !== jsonData.sync_outgoing) {
            changed = true;
            this.sync_outgoing = jsonData.sync_outgoing;
        }
        return changed;
    }
}
export const LastSync_columns = [
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
tables["LastSync"] = LastSync_columns;
export class _Oauth1token {
    revision : number;
    id : number;
    provider_name : string;
    oauth_token : string;
    oauth_token_secret : string;
    user_id : number;
    constructor(jsonData:Record<string,any>, revision=0) {
        this.id = jsonData.id;
        this.update(jsonData, revision);
    }

    _log: [string, string][] = [];
    log(level: string, msg?: string) {
        if (msg !== undefined) this._log.unshift([level, msg]);
        else this._log.unshift(['info', level]);
    }
    clear_log() {
        this._log = [];
    }
    update(jsonData:Record<string,any>, revision=0) : boolean {
        if(this.id !== jsonData.id) throw new Error("Data doesn't match ID");
        this.revision = revision;
        let changed = false;
        if(this.provider_name !== jsonData.provider_name) {
            changed = true;
            this.provider_name = jsonData.provider_name;
        }
        if(this.oauth_token !== jsonData.oauth_token) {
            changed = true;
            this.oauth_token = jsonData.oauth_token;
        }
        if(this.oauth_token_secret !== jsonData.oauth_token_secret) {
            changed = true;
            this.oauth_token_secret = jsonData.oauth_token_secret;
        }
        if(this.user_id !== jsonData.user_id) {
            changed = true;
            this.user_id = jsonData.user_id;
        }
        return changed;
    }
}
export const Oauth1token_columns = [
    {
        name: "id",
        type: "int",
    },
    {
        name: "provider_name",
        type: "str",
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
tables["Oauth1token"] = Oauth1token_columns;
export class _Oauth2token {
    revision : number;
    id : number;
    provider_name : string;
    token_type : string;
    access_token : string;
    refresh_token : string;
    expires_at : Date;
    user_id : number;
    constructor(jsonData:Record<string,any>, revision=0) {
        this.id = jsonData.id;
        this.update(jsonData, revision);
    }

    _log: [string, string][] = [];
    log(level: string, msg?: string) {
        if (msg !== undefined) this._log.unshift([level, msg]);
        else this._log.unshift(['info', level]);
    }
    clear_log() {
        this._log = [];
    }
    update(jsonData:Record<string,any>, revision=0) : boolean {
        if(this.id !== jsonData.id) throw new Error("Data doesn't match ID");
        this.revision = revision;
        let changed = false;
        if(this.provider_name !== jsonData.provider_name) {
            changed = true;
            this.provider_name = jsonData.provider_name;
        }
        if(this.token_type !== jsonData.token_type) {
            changed = true;
            this.token_type = jsonData.token_type;
        }
        if(this.access_token !== jsonData.access_token) {
            changed = true;
            this.access_token = jsonData.access_token;
        }
        if(this.refresh_token !== jsonData.refresh_token) {
            changed = true;
            this.refresh_token = jsonData.refresh_token;
        }
        if(this.expires_at !== jsonData.expires_at) {
            changed = true;
            this.expires_at = jsonData.expires_at;
        }
        if(this.user_id !== jsonData.user_id) {
            changed = true;
            this.user_id = jsonData.user_id;
        }
        return changed;
    }
}
export const Oauth2token_columns = [
    {
        name: "id",
        type: "int",
    },
    {
        name: "provider_name",
        type: "str",
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
tables["Oauth2token"] = Oauth2token_columns;
export class _CourseUser {
    revision : number;
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
    constructor(jsonData:Record<string,any>, revision=0) {
        this.id = jsonData.id;
        this.course_id = jsonData.course_id;
        this.course_canvas_id = jsonData.course_canvas_id;
        this.update(jsonData, revision);
    }

    _log: [string, string][] = [];
    log(level: string, msg?: string) {
        if (msg !== undefined) this._log.unshift([level, msg]);
        else this._log.unshift(['info', level]);
    }
    clear_log() {
        this._log = [];
    }
    update(jsonData:Record<string,any>, revision=0) : boolean {
        if(this.id !== jsonData.id) throw new Error("Data doesn't match ID");
        this.revision = revision;
        let changed = false;
        if(this.lastname !== jsonData.lastname) {
            changed = true;
            this.lastname = jsonData.lastname;
        }
        if(this.firstname !== jsonData.firstname) {
            changed = true;
            this.firstname = jsonData.firstname;
        }
        if(this.email !== jsonData.email) {
            changed = true;
            this.email = jsonData.email;
        }
        if(this.is_admin !== jsonData.is_admin) {
            changed = true;
            this.is_admin = jsonData.is_admin;
        }
        if(this.locale !== jsonData.locale) {
            changed = true;
            this.locale = jsonData.locale;
        }
        if(this.role !== jsonData.role) {
            changed = true;
            this.role = jsonData.role;
        }
        if(this.course_name !== jsonData.course_name) {
            changed = true;
            this.course_name = jsonData.course_name;
        }
        if(this.course_slug !== jsonData.course_slug) {
            changed = true;
            this.course_slug = jsonData.course_slug;
        }
        return changed;
    }
}
export const CourseUser_columns = [
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
        hide: true,
        icons: {"true": "\ud83e\uddd1\u200d\ud83d\udcbb", "": " "},
    },
    {
        name: "locale",
        type: "str",
    },
    {
        name: "course_id",
        type: "int",
        immutable: true,
    },
    {
        name: "role",
        type: "str",
        icons: {"student": "\ud83e\uddd1\u200d\ud83c\udf93", "ta": "\ud83e\uddd1\u200d\ud83d\udcbb", "teacher": "\ud83e\uddd1\u200d\ud83c\udfeb", "admin": "\ud83e\uddd1\u200d\ud83d\udcbc", "": "\ud83e\udd37"},
        access: {"write": "admin", "read": "peer"},
    },
    {
        name: "course_canvas_id",
        type: "int",
        view: {"course_user": "course_canvas_id"},
        immutable: true,
        form: "canvas_course",
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
        form: {"slugify": "name"},
    },
]
tables["CourseUser"] = CourseUser_columns;
export class _UserAccount {
    revision : number;
    id : number;
    canvas_id? : number;
    canvas_username? : string;
    gitlab_id? : number;
    gitlab_username? : string;
    discord_id? : number;
    discord_username? : string;
    constructor(jsonData:Record<string,any>, revision=0) {
        this.id = jsonData.id;
        this.update(jsonData, revision);
    }

    _log: [string, string][] = [];
    log(level: string, msg?: string) {
        if (msg !== undefined) this._log.unshift([level, msg]);
        else this._log.unshift(['info', level]);
    }
    clear_log() {
        this._log = [];
    }
    update(jsonData:Record<string,any>, revision=0) : boolean {
        if(this.id !== jsonData.id) throw new Error("Data doesn't match ID");
        this.revision = revision;
        let changed = false;
        if(this.canvas_id !== jsonData.canvas_id) {
            changed = true;
            this.canvas_id = jsonData.canvas_id;
        }
        if(this.canvas_username !== jsonData.canvas_username) {
            changed = true;
            this.canvas_username = jsonData.canvas_username;
        }
        if(this.gitlab_id !== jsonData.gitlab_id) {
            changed = true;
            this.gitlab_id = jsonData.gitlab_id;
        }
        if(this.gitlab_username !== jsonData.gitlab_username) {
            changed = true;
            this.gitlab_username = jsonData.gitlab_username;
        }
        if(this.discord_id !== jsonData.discord_id) {
            changed = true;
            this.discord_id = jsonData.discord_id;
        }
        if(this.discord_username !== jsonData.discord_username) {
            changed = true;
            this.discord_username = jsonData.discord_username;
        }
        return changed;
    }
}
export const UserAccount_columns = [
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
tables["UserAccount"] = UserAccount_columns;
export class _FullUser {
    revision : number;
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
    canvas_id? : number;
    canvas_username? : string;
    gitlab_id? : number;
    gitlab_username? : string;
    discord_id? : number;
    discord_username? : string;
    constructor(jsonData:Record<string,any>, revision=0) {
        this.id = jsonData.id;
        this.course_id = jsonData.course_id;
        this.course_canvas_id = jsonData.course_canvas_id;
        this.update(jsonData, revision);
    }

    _log: [string, string][] = [];
    log(level: string, msg?: string) {
        if (msg !== undefined) this._log.unshift([level, msg]);
        else this._log.unshift(['info', level]);
    }
    clear_log() {
        this._log = [];
    }
    update(jsonData:Record<string,any>, revision=0) : boolean {
        if(this.id !== jsonData.id) throw new Error("Data doesn't match ID");
        this.revision = revision;
        let changed = false;
        if(this.lastname !== jsonData.lastname) {
            changed = true;
            this.lastname = jsonData.lastname;
        }
        if(this.firstname !== jsonData.firstname) {
            changed = true;
            this.firstname = jsonData.firstname;
        }
        if(this.email !== jsonData.email) {
            changed = true;
            this.email = jsonData.email;
        }
        if(this.is_admin !== jsonData.is_admin) {
            changed = true;
            this.is_admin = jsonData.is_admin;
        }
        if(this.locale !== jsonData.locale) {
            changed = true;
            this.locale = jsonData.locale;
        }
        if(this.role !== jsonData.role) {
            changed = true;
            this.role = jsonData.role;
        }
        if(this.course_name !== jsonData.course_name) {
            changed = true;
            this.course_name = jsonData.course_name;
        }
        if(this.course_slug !== jsonData.course_slug) {
            changed = true;
            this.course_slug = jsonData.course_slug;
        }
        if(this.canvas_id !== jsonData.canvas_id) {
            changed = true;
            this.canvas_id = jsonData.canvas_id;
        }
        if(this.canvas_username !== jsonData.canvas_username) {
            changed = true;
            this.canvas_username = jsonData.canvas_username;
        }
        if(this.gitlab_id !== jsonData.gitlab_id) {
            changed = true;
            this.gitlab_id = jsonData.gitlab_id;
        }
        if(this.gitlab_username !== jsonData.gitlab_username) {
            changed = true;
            this.gitlab_username = jsonData.gitlab_username;
        }
        if(this.discord_id !== jsonData.discord_id) {
            changed = true;
            this.discord_id = jsonData.discord_id;
        }
        if(this.discord_username !== jsonData.discord_username) {
            changed = true;
            this.discord_username = jsonData.discord_username;
        }
        return changed;
    }
}
export const FullUser_columns = [
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
        hide: true,
        icons: {"true": "\ud83e\uddd1\u200d\ud83d\udcbb", "": " "},
    },
    {
        name: "locale",
        type: "str",
    },
    {
        name: "course_id",
        type: "int",
        immutable: true,
    },
    {
        name: "role",
        type: "str",
        icons: {"student": "\ud83e\uddd1\u200d\ud83c\udf93", "ta": "\ud83e\uddd1\u200d\ud83d\udcbb", "teacher": "\ud83e\uddd1\u200d\ud83c\udfeb", "admin": "\ud83e\uddd1\u200d\ud83d\udcbc", "": "\ud83e\udd37"},
        access: {"write": "admin", "read": "peer"},
    },
    {
        name: "course_canvas_id",
        type: "int",
        view: {"course_user": "course_canvas_id"},
        immutable: true,
        form: "canvas_course",
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
        form: {"slugify": "name"},
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
tables["FullUser"] = FullUser_columns;
