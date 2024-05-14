import { html, render } from 'uhtml';
import {
    _Course,
    _FullUser,
    _User,
    _Group,
    _Membership,
    _Assignment,
    Course_columns,
    Assignment_columns,
    _Account,
    _Project,
    _CourseUser,
    tables,
    PRIVILEGED_ROLES,
} from './model_gen';
export { tables } from './model_gen';
import { request, puffin, to_table, gitlab_url, handle_internal_link, user_emails } from './puffin';
import { CourseView } from './courses';
import { BorbPanelBuilder } from '../borb/Frames';

export type Membership = _Membership;
export class Group extends _Group {
    _original: _Group;
    members: Member[];
    course: Course;
    constructor(jsonData: Record<string, any>, course: Course) {
        super(jsonData);
        this.course = course;
    }

    as_link(link_text: string = undefined) {
        link_text = link_text ? link_text : this.slug;
        return html`<a data-type="group" data-target=${this.id} onclick=${handle_internal_link} href=${`group://${this.id}`}>${link_text}</a>`;
    }

    get users(): User[] {
        return this.members.map(m => this.course.usersById[m.user_id])
    }

    display(panel: HTMLElement = undefined) {
        panel = panel ? panel : new BorbPanelBuilder()
            .frame('frame2')
            .panel('div', 'group_display')
            .title(this.name)
            .select(true)
            .done();
        const table1 = to_table({ _type: 'Member[]', data: this.members, selectable: false });
        const debug = puffin.debug['console'] ? html`<div><button type="button" onclick=${() => console.log(this)}>Debug</button></div>` : '';
        const children = this.children;
        const children_table = children.length > 0 ? to_table({ _type: 'Group[]', data: children, selectable: false }) : '';
        const title = this.json_data.project_path ? html`<a href="${gitlab_url(this.json_data.project_path)}" target="_blank"> ${this.json_data.project_name} – [${this.json_data.project_path}]</a>` : this.json_data.project_name;
        render(
            panel,
            html`
                ${this.kind === 'team'
                    ? html`<h2>Team ${this.name} ${this.parent ? html`(${this.parent.as_link()})` : ''}</h2>
                          <b>Project:</b> ${title}`
                    : html`<h2>Group/${this.kind} ${this.name}</h2>`}
                <div><borb-sheet>${table1}</borb-sheet></div>
                ${this.join_source ? html`<p>(members imported from ${this.join_source})</p>` : ''}
                <div><b>Email:</b> ${user_emails(this.users)}</div>
                <div><borb-sheet>${children_table}</borb-sheet></div>
                ${debug}
            `,
        );
    }

    async sync_with_gitlab() {
        await request(`courses/${this.course_id}/groups/${this.id}/sync`);
    }

    get parent() {
        return this.course.groupsById[this.parent_id];
    }

    get children() {
        return this.course.groups.filter(g => g.parent_id === this.id);
    }
}
export const Team_columns = [
    {
        name: "id",
        type: "int",
    },
    {
        name: "parent_id",
        type: "custom",
        mapping: (field, obj: Group, spec) => html.node`${obj.parent?.as_link()}`
    },
    {
        name: "name",
        type: "str",
        access: { "write": "member" },
    },
    {
        name: "slug",
        type: "group.slug",
        form: { "slugify": "name" },
    },
    {
        name: "project",
        type: "custom",
        mapping: (field, obj, spec) => html.node`<a href="${gitlab_url(obj.json_data.project_path)}" target="_blank">${obj.json_data.project_name}</a>`
    },
    /*    {
            name: "json_data",
            type: "dict",
        },*/
]
tables["Team"] = Team_columns;

export class Project extends _Project {
    full_path(): string {
        if (this.namespace_slug) return this.namespace_slug + '/' + this.slug;
        else return this.slug;
    }
}
export class Assignment extends _Assignment {
    _original: _Assignment;
    _project_ref: string;
    _test_project_ref: string;
    _error: string;
    _created: boolean;
    _gitlab_path: string;
    _gitlab_root_path: string;
    _gitlab_test_path: string;
    _course: Course;
    gitlab_project: Project;
    _gitlab_project: Project;
    gitlab_root_project: Project;
    _gitlab_root_project: Project;
    gitlab_test_project: Project;
    _gitlab_test_project: Project;
    set course(course: Course) {
        this._course = course;
        this.course_id = course.external_id;
    }
    get course(): Course {
        return this._course;
    }

    as_link(link_text: string = undefined) {
        link_text = link_text ? link_text : this.slug;
        return html`<a data-type="assignment" data-target=${this.id} onclick=${handle_internal_link} href=${`group://${this.id}`}>${link_text}</a>`;
    }
    has_valid_gitlab_path() {
        console.log(this);
        if (!this._gitlab_path) this._gitlab_path = `${this.gitlab_id}`;
        return this.gitlab_id && this.json_data['gitlab_path'] === this._gitlab_path;
    }
    has_valid_gitlab_test_path() {
        console.log(this);
        if (!this._gitlab_test_path) this._gitlab_test_path = this.json_data['gitlab_test_path'];
        return (
            this.json_data['gitlab_test_path'] &&
            this.json_data['gitlab_test_path'] === this._gitlab_test_path
        );
    }
    async updateAssignment(): Promise<Assignment> {
        if (this.course && this.id) {
            const data = await request(`courses/${this.course.external_id}/${this.id}`);
            this.revision++;
            this.update(data, this.revision);
            this._original = data;
        } else if (this._original) {
            this.update(this._original);
        }
        delete this._gitlab_path;
        delete this._gitlab_root_path;
        delete this._gitlab_test_path;
        return this;
    }
    diff() {
        const diff = {};
        if (!this._original) this._original = {} as any;
        Assignment_columns.forEach((col) => {
            const name = col.name;
            // if(col.type === 'dict')
            if (this._original[name] !== this[name]) {
                diff[name] = this[name];
            }
        });
        return diff;
    }
}
export class User extends _FullUser {
    _original: _User;
    groups: Group[];

    get team() {
        return this.groups.filter(g => g.kind === 'team')
    }
    get section() {
        return this.groups.filter(g => g.kind === 'section')
    }
    as_link(link_text: string = undefined) {
        link_text = link_text ? link_text : `${this.firstname} ${this.lastname}`;
        return html`<a data-type="user" data-target=${this.id} onclick=${handle_internal_link} href=${`group://${this.id}`}>${link_text}</a>`;
    }
    get is_privileged() {
        return PRIVILEGED_ROLES.indexOf(this.role) != -1;
    }
}
export class SelfUser extends _User {
    gitlab_account?: _Account;
    canvas_account?: _Account;
    discord_account?: _Account;
    course_user?: User;
    on_update?: () => void;
    login_required?: true;
}
function to_arraymap<T extends { id: number }>(array: T[]) {
    const arraymap: T[] = [];
    array.forEach((v, i) => {
        arraymap[v.id] = v;
    });
    return arraymap;
}
export type Member = {
    user_id: number;
    username: string;
    firstname: string;
    lastname: string;
    role: string;
    join_model: string;
};
export const Member_columns = [
    {
        name: 'role',
        type: 'str',
        icons: {
            student: '\ud83e\uddd1\u200d\ud83c\udf93',
            ta: '\ud83e\uddd1\u200d\ud83d\udcbb',
            teacher: '\ud83e\uddd1\u200d\ud83c\udfeb',
            admin: '\ud83e\uddd1\u200d\ud83d\udcbc',
            '': '\ud83e\udd37',
        },
    },
    {
        name: 'lastname',
        type: 'str',
    },
    {
        name: 'firstname',
        type: 'str',
    },
    {
        name: 'join_model',
        type: 'JoinModel',
    },
];
tables['Member'] = Member_columns;

export class Course extends _Course {
    public static courses: Course[] = [];
    public static current: Course = null;
    static current_user: SelfUser;

    _original: _Course;
    _gitlab_path: string;
    _gitlab_student_path: string;
    public users: User[] = [];
    public usersById: User[] = [];
    public groups: Group[] = [];
    public groupsById: Group[] = [];
    public groupsBySlug: Map<string, Group> = new Map();

    has_valid_gitlab_path() {
        if (!this._gitlab_path) this._gitlab_path = this.json_data['gitlab_path'];
        return this.json_data['gitlab_path'] && this.json_data['gitlab_path'] === this._gitlab_path;
    }
    has_valid_gitlab_student_path() {
        if (!this._gitlab_student_path)
            this._gitlab_student_path = this.json_data['gitlab_student_path'];
        return (
            this.json_data['gitlab_student_path'] &&
            this.json_data['gitlab_student_path'] === this._gitlab_student_path
        );
    }

    diff() {
        const diff = {};
        if (!this._original) this._original = {} as any;
        Course_columns.forEach((col) => {
            const name = col.name;
            // if(col.type === 'dict')
            if (this._original[name] !== this[name]) {
                diff[name] = this[name];
            }
        });
        return diff;
    }
    static async updateCourses(): Promise<Course[]> {
        const courses = (await request('courses/')) as _Course[];
        const activeCourses: Set<number> = new Set();
        courses.forEach((c) => {
            activeCourses.add(c.external_id);
            if (Course.courses[c.external_id]) {
                Course.courses[c.external_id].updateCourse(c);
            } else {
                Course.courses[c.external_id] = new Course(c);
                Course.courses[c.external_id]._original = c;
            }
        });
        const removed = Course.courses.filter((c) => !activeCourses.has(c.external_id));
        removed.forEach((c) => {
            console.warn('Removed course: ', c);
        });
        CourseView.update_course_list();
        return [...Course.courses];
    }
    static async setActiveCourse(course_id: number, update = true): Promise<Course> {
        let course = Course.courses[course_id];
        if (!course) {
            const data = await request(`courses/${course_id}`);
            Course.courses[course_id] = course = new Course(data);
            course._original = data;
        }
        return await course.setActive(update);
    }
    async setActive(update = true): Promise<Course> {
        Course.current = this;
        if (update) await this.updateCourse();
        Course.current_user.course_user = this.currentUser();
        Course.current_user?.on_update();
        CourseView.update_course_list();
        //CourseView.refresh(true, false);

        return Promise.resolve(Course.current);
    }
    currentUser(): User {
        return this.usersById[Course.current_user.id];
    }
    async updateCourse(data: _Course = undefined): Promise<Course> {
        data = data || (await request(`courses/${this.external_id}/`));
        this.revision++;
        this.update(data, this.revision);
        this._original = data;
        delete this._gitlab_path;
        delete this._gitlab_student_path;
        await this.updateUsers();
        await this.updateGroups();
        await this.updateMemberships();
        return this;
    }
    async updateUsers(): Promise<User[]> {
        const us: _User[] = await request(`courses/${this.external_id}/users/?accounts=true`);
        this.users = [];
        us.forEach((u) => {
            const user = this.usersById[u.id] || new User(u);
            user.update(u, this.revision);
            user._original = u;
            this.users.push(user);
        });
        this.usersById = to_arraymap(this.users);
        return this.users;
    }
    async updateGroups(): Promise<Group[]> {
        const gs: _Group[] = await request(`courses/${this.external_id}/groups/`);
        this.groups = [];
        this.groupsBySlug.clear();
        gs.forEach((g) => {
            const group = this.groupsById[g.id] || new Group(g, this);
            group.update(g, this.revision);
            group._original = g;
            this.groups.push(group);
            this.groupsBySlug.set(group.slug, group);
        });
        this.groupsById = to_arraymap(this.groups);
        return this.groups;
    }
    async updateMemberships() {
        const members = (await request(`courses/${this.external_id}/memberships/`)) as Membership[];
        console.log('groups', this.groups, 'members', members);
        this.groups.forEach((g) => (g.members = []));
        this.users.forEach((u) => (u.groups = []));
        members.forEach((m) => {
            const g = this.groupsById[m.group_id];
            const u = this.usersById[m.user_id];
            g.members.push({
                user_id: m.user_id,
                username: u.canvas_username,
                lastname: u.lastname,
                firstname: u.firstname,
                role: m.role,
                join_model: m.join_model,
            });
            u.groups.push(g);
        });
    }

    clone_team_projects() {
        return this.groups.filter(g => g.kind === 'team').map(t => `[ ! -f ${t.slug} ] && git clone git@git.app.uib.no:${t.json_data.project_path} ${t.slug} && sleep 2`);
    }
    as_link(link_text: string = undefined) {
        link_text = link_text ? link_text : `${this.slug}`;
        return html`<a data-type="course" data-target=${this.id} onclick=${handle_internal_link} href=${`group://${this.id}`}>${link_text}</a>`;
    }
}
