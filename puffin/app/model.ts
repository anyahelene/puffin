import { Hole, html, render } from 'uhtml';
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
    Membership_columns,
} from './model_gen';
export { tables } from './model_gen';
import {
    request,
    puffin,
    to_table,
    gitlab_url,
    handle_internal_link,
    user_emails,
    readable_size,
} from './puffin';
import { CourseView } from './courses';
import { BorbPanelBuilder } from '../borb/Frames';
import { BorbButton } from '../borb/Buttons';
import { show_flash } from './flashes';
import { edit_assignment_form } from './assignments';

type Membership = _Membership;
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
        return html`<a
            data-type="group"
            data-target=${this.id}
            onclick=${handle_internal_link}
            href=${`group://${this.id}`}
            >${link_text}</a
        >`;
    }

    get users(): User[] {
        return this.members.map((m) => this.course.usersById[m.user_id]);
    }
    get students(): User[] {
        return this.members
            .filter((m) => m.role === 'student')
            .map((m) => this.course.usersById[m.user_id]);
    }
    isMember(u: User | SelfUser) {
        return this.members.findIndex((m) => m.user_id === u.id) != -1;
    }
    isStudent(u: User | SelfUser) {
        return this.members.findIndex((m) => m.role === 'student' && m.user_id === u.id) != -1;
    }
    display(panel: HTMLElement = undefined) {
        panel = panel
            ? panel
            : new BorbPanelBuilder()
                  .frame('frame2')
                  .panel('div', `group_${this.slug}_display`)
                  .title(this.name)
                  .select(true)
                  .done();
        const setPerm = async (ev: Event) => {
            const elt = ev.currentTarget as BorbButton;
            if (elt.name) {
                console.log('setPerm', elt.checked, elt.dataset.filename);
                elt.dataset.status = 'pending';
                const checked = elt.checked;
                const data = {};
                data[elt.name] = checked;
                const result = await request(
                    `courses/${this.course.external_id}/teams/${this.id}/share`,
                    'PUT',
                    data,
                    false,
                    true,
                );
                console.log('result', result);
                if (result.status === 'error') {
                    elt.dataset.status = 'error';
                    show_flash(result, 'error');
                } else {
                    this.update(result);
                    console.log('setPerm', this.json_data, this.json_data.share[elt.name], checked);
                    if (checked !== this.json_data.share[elt.name])
                        show_flash(`Failed to update ${elt.name} for ${this.slug}`, 'warning');
                    else
                        show_flash(
                            `${checked ? 'Enabled' : 'Disabled'} ${elt.name} for ${this.slug}`,
                        );
                    setTimeout(() => {
                        elt.dataset.status = 'ok';
                        redraw();
                    }, 200);
                }
            }
        };
        const redraw = () => {
            const isStudent = this.isStudent(Course.current_user) || Course.current_user.is_admin;
            const isMember = this.isMember(Course.current_user) || Course.current_user.is_admin;
            const table1 = to_table({
                _type: 'Member[]',
                data: this.members.filter((m) => m.role === 'student'),
                selectable: false,
            });
            const debug = puffin.debug['console']
                ? html`<div
                      ><button type="button" onclick=${() => console.log(this)}>Debug</button></div
                  >`
                : '';
            const children = this.children;
            const children_table =
                children.length > 0
                    ? to_table({ _type: 'Group[]', data: children, selectable: false })
                    : '';
            const title = this.json_data.project_path
                ? html`<a href="${gitlab_url(this.json_data.project_path)}" target="_blank">
                      ${this.json_data.project_name} – [${this.json_data.project_path}]</a
                  >`
                : this.json_data.project_name || '(none)';
            const filesPath = `courses/${this.course.external_id}/teams/${this.id}/files/`;
            const share = this.json_data.share || {};
            console.log('redraw', this.json_data.share_jar, JSON.stringify(this.json_data));
            const has_members = this.students.length > 0;
            let sharing = [];
            const SHARING_ENABLED = false; // TODO
            if (this.kind === 'team' && SHARING_ENABLED) {
                sharing.push(
                    html`<b>Readme:</b> ${share.readme_file &&
                        (isMember || share.share_src || share.share_jar)
                            ? html`<a href=${filesPath + share.readme_file} target="_blank"
                                  >${share.readme_file}</a
                              >`
                            : html`<em>(private)</em>`}<br />`,
                );
                if (isStudent) {
                    sharing.push(html`<b>Share source code:</b>
                        <borb-button
                            type="switch"
                            name="share_src"
                            data-filename=${share.src_file}
                            onchange=${setPerm}
                            ?disabled=${!isStudent}
                            ?checked=${share.share_src}
                        ></borb-button>
                        ${share.src_file && (isStudent || share.share_src)
                            ? html`(<a href=${filesPath + share.src_file} download
                                      >${share.src_file}</a
                                  >, ${readable_size(share.src_size)})`
                            : ''}<br />`);
                    sharing.push(html`<b>Share JAR file:</b>
                        <borb-button
                            type="switch"
                            name="share_jar"
                            data-filename=${share.jar_file}
                            onchange=${setPerm}
                            ?disabled=${!isStudent}
                            ?checked=${share.share_jar}
                        ></borb-button>
                        ${share.jar_file && (isStudent || share.share_jar)
                            ? html`(<a href=${filesPath + share.jar_file} download
                                      >${share.jar_file}</a
                                  >, ${readable_size(share.jar_size)})`
                            : ''}<br />`);
                } else {
                    sharing.push(
                        html`<b>Source code:</b> ${share.src_file && (isMember || share.share_src)
                                ? html`<a href=${filesPath + share.src_file} download
                                          >${share.src_file}</a
                                      >
                                      (${readable_size(share.src_size)})`
                                : html`<em>(private)</em>`}<br />`,
                    );
                    sharing.push(
                        html`<b>Runnable JAR file:</b> ${share.jar_file &&
                            (isMember || share.share_jar)
                                ? html`<a href=${filesPath + share.jar_file} download
                                          >${share.jar_file}</a
                                      >
                                      (${readable_size(share.jar_size)})`
                                : html`<em>(private)</em>`}<br />`,
                    );
                }
                (share.screenshots || []).forEach((entry) => {
                    const name = entry[0],
                        size = entry[1];
                    sharing.push(
                        html`<a href=${filesPath + name} target="_blank"
                            ><img src=${filesPath + name} width="300"
                        /></a> `,
                    );
                });
            }
            const sync_group = async () => {
                const result = await request(`courses/${this.course.external_id}/groups/${this.id}/sync`, 'POST');
                console.log('sync_group', result);
                await Course.current.updateMemberships();
                redraw();
            }
            render(
                panel,
                html`
                    ${this.kind === 'team'
                        ? html`<h2
                                  >Team ${this.name}
                                  ${this.parent ? html`(${this.parent.as_link()})` : ''}</h2
                              >
                              <b>Project:</b> ${title}<br />`
                        : html`<h2>Group/${this.kind} ${this.name}</h2>`}
                    ${sharing}
                    ${has_members
                        ? html` <div><borb-sheet>${table1}</borb-sheet></div>
                              ${this.join_source
                                  ? html`<p>(members imported from ${this.join_source} <button type="button" onclick=${sync_group}>Sync now!</button>)</p>`
                                  : ''}
                              <p><b>Emails:</b> ${user_emails(this.students)}</p>
                              <div><borb-sheet>${children_table}</borb-sheet></div>
                              ${debug}`
                        : ''}
                `,
            );
        };
        redraw();
    }

    get_file_link(kind) {
        const filesPath = `courses/${this.course.external_id}/teams/${this.id}/files/`;
        const share = this.json_data.share || {};
        if (share[`${kind}_file`]) {
            if (share[`share_${kind}`]) {
                return html.node`<a href=${filesPath + share[`${kind}_file`]} download>${
                    share[`${kind}_file`]
                }</a> (${readable_size(share[`${kind}_size`])})`;
            } else if (kind === 'readme') {
                return html.node`<a href=${
                    filesPath + share[`${kind}_file`]
                } target="_blank">README.md</a>`;
            }
        }
        return '';
    }

    async sync_with_gitlab() {
        await request(`courses/${this.course_id}/groups/${this.id}/sync`);
    }

    get parent() {
        return this.course.groupsById[this.parent_id];
    }

    get children() {
        return this.course.groups.filter((g) => g.parent_id === this.id);
    }
}
export const Team_columns = [
    {
        name: 'id',
        type: 'int',
    },
    {
        name: 'parent_id',
        type: 'custom',
        mapping: (field, obj: Group, spec) => html.node`${obj.parent?.as_link()}`,
    },
    {
        name: 'name',
        head: 'Team name',
        type: 'custom',
        access: { write: 'member' },
        mapping: (field, obj: Group, spec) => html.node`${obj.as_link(obj.name)}`,
    },
    {
        name: 'slug',
        head: 'Short name',
        type: 'group.slug',
        form: { slugify: 'name' },
    },
    {
        name: 'project',
        head: 'Git project',
        type: 'custom',
        mapping: (field, obj, spec) =>
            obj.json_data.project_path
                ? html.node`<a href="${gitlab_url(obj.json_data.project_path)}" target="_blank">${
                      obj.json_data.project_name
                  }</a>`
                : '',
    },
    {
        name: 'share_readme',
        head: 'Project README',
        type: 'custom',
        mapping: (field, obj: Group, spec) => obj.get_file_link('readme'),
    },
    {
        name: 'share_jar',
        head: 'Runnable JAR',
        type: 'custom',
        mapping: (field, obj: Group, spec) => obj.get_file_link('jar'),
    },
    {
        name: 'share_src',
        head: 'Source code',
        type: 'custom',
        mapping: (field, obj: Group, spec) => obj.get_file_link('src'),
    },
    /*    {
            name: "json_data",
            type: "dict",
        },*/
];
tables['Team'] = Team_columns;

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

    constructor(jsonData: Record<string, any> | _Assignment, course: Course, revision?: number) {
        super(jsonData, revision);
        this.course = course;
    }
    set course(course: Course) {
        this._course = course;
        this.course_id = course.external_id;
    }
    get course(): Course {
        return this._course;
    }

    as_link(link_text: string = undefined) {
        link_text = link_text ? link_text : this.slug;
        return html`<a
            data-type="assignment"
            data-target=${this.id}
            onclick=${handle_internal_link}
            href=${`assignment://${this.id}`}
            >${link_text}</a
        >`;
    }
    has_valid_gitlab_path() {
        console.log(this);
        if (!this._gitlab_path) this._gitlab_path = this.json_data['gitlab_path'];
        return this.json_data['gitlab_path'] && this.json_data['gitlab_path'] === this._gitlab_path;
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
            const data = await request(`courses/${this.course.external_id}/assignments/${this.id}`);
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
    display() {
        console.log('display assignment', this);
        edit_assignment_form(this);
    }
}
export class User extends _FullUser {
    _original: _User;
    groups: Group[];
    memberships: Map<number, Member> = new Map();

    findGroups({ kind, role }: { kind: string; role: string }) {
        let result = this.groups;
        if (kind !== undefined) result = result.filter((g) => g.kind === kind);
        if (role !== undefined)
            result = result.filter((g) => this.memberships.get(g.id).role === role);
        return result;
    }
    get team() {
        return this.groups.filter(
            (g) => g.kind === 'team' && this.memberships.get(g.id).role === this.role,
        );
    }
    get section() {
        return this.groups.filter((g) => g.kind === 'section');
    }
    get group() {
        return this.groups.filter(
            (g) => g.kind === 'group' && this.memberships.get(g.id).role === this.role,
        );
    }

    as_link(link_text: string = undefined) {
        link_text = link_text ? link_text : `${this.firstname} ${this.lastname}`;
        return html`<a
            data-type="user"
            data-target=${this.id}
            onclick=${handle_internal_link}
            href=${`user://${this.id}`}
            >${link_text}</a
        >`;
    }
    get is_privileged() {
        return PRIVILEGED_ROLES.indexOf(this.role) != -1;
    }
    display() {
        console.log('display user', this);
    }
}
export class SelfUser extends _User {
    gitlab_account?: _Account;
    canvas_account?: _Account;
    discord_account?: _Account;
    course_user?: User;
    on_update?: () => void;
    login_required?: true;
    real_id: number;
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
        icons: Membership_columns.find((c) => c.name === 'role').icons,
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
    public assignments: Assignment[] = [];
    public assignmentsBySlug: Map<string, Assignment> = new Map();
    public assignmentsById: Assignment[] = [];

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
    static async updateCourses(update_ui = true): Promise<Course[]> {
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
        if (update_ui) CourseView.update_course_list();
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
        localStorage.setItem('active-course', `${this.external_id}`);
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
        await this.updateAssignments();
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
            const m2: Member = {
                user_id: m.user_id,
                username: u?.canvas_username,
                lastname: u?.lastname,
                firstname: u?.firstname,
                role: m.role,
                join_model: m.join_model,
            };
            g.members.push(m2);
            u?.groups.push(g);
            u?.memberships.set(m.group_id, m2);
        });
    }
    async updateAssignments(): Promise<Assignment[]> {
        const as: _Assignment[] = await request(`courses/${this.external_id}/assignments/`);
        this.assignments = [];
        this.assignmentsBySlug.clear();
        as.forEach((a) => {
            const asgn = this.assignmentsById[a.id] || new Assignment(a, this);
            asgn.update(a, this.revision);
            asgn._original = a;
            this.assignments.push(asgn);
            this.assignmentsBySlug.set(asgn.slug, asgn);
        });
        this.assignmentsById = to_arraymap(this.assignments);
        return this.assignments;
    }

    get term() : string {
        return this.slug.split('-', 2)[1];
    }
    get code() : string {
        return this.slug.split('-', 2)[0];
    }
    
    clone_team_projects() {
        return this.groups
            .filter((g) => g.kind === 'team')
            .map(
                (t) =>
                    `[ ! -f ${t.slug} ] && git clone git@git.app.uib.no:${t.json_data.project_path} ${t.slug} && sleep 2`,
            );
    }
    as_link(link_text: string = undefined) {
        link_text = link_text ? link_text : `${this.slug}`;
        return html`<a
            data-type="course"
            data-target=${this.id}
            onclick=${handle_internal_link}
            href=${`group://${this.id}`}
            >${link_text}</a
        >`;
    }
}

export class GitlabProject extends Project {
    [key: string]: any;

    constructor(jsonData: Record<string, any>, revision?: number) {
        super(jsonData, revision);
    }
}
