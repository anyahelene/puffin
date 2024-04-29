import { html, render } from 'uhtml';
import {
    _Course,
    _FullUser,
    _User,
    _Group,
    _Membership,
    tables as _tables,
    _Assignment,
    Course_columns,
    Assignment_columns,
    _Account,
    _Project,
    _CourseUser,
} from './model_gen';
import { request, puffin } from './puffin';
import { CourseView } from './courses';

export const tables = _tables;
export type Membership = _Membership;
export class Group extends _Group {
    _original: _Group;
    members: Member[];
}
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
}
export class SelfUser extends _User {
    gitlab_account?: _Account;
    canvas_account?: _Account;
    discord_account?: _Account;
    course_user?: _CourseUser;
    on_update?: () => void;
}
function to_arraymap<T extends { id: number }>(array: T[]) {
    const arraymap: T[] = [];
    array.forEach((v, i) => {
        arraymap[v.id] = v;
    });
    return arraymap;
}
export type Member = {
    id: number;
    slug: string;
    firstname: string;
    lastname: string;
    role: string;
    join_model: string;
};

export class Course extends _Course {
    public static courses = [];
    public static current = null;
    static current_user: SelfUser;

    _original: _Course;
    _gitlab_path: string;
    _gitlab_student_path: string;
    public users: User[] = [];
    public usersById: User[] = [];
    public groups: Group[] = [];
    public groupsById: Group[] = [];

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
        Course.current_user.course_user = this.currentUser();
        Course.current_user?.on_update();
        if(update)
            await this.updateCourse();
        CourseView.update_course_list();
        CourseView.refresh(true, false);

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
        const us: _User[] = await request(`courses/${this.external_id}/users?accounts=true`);
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
        const gs: _Group[] = await request(`courses/${this.external_id}/groups`);
        this.groups = [];
        gs.forEach((g) => {
            const group = this.groupsById[g.id] || new Group(g);
            group.update(g, this.revision);
            group._original = g;
            this.groups.push(group);
        });
        this.groupsById = to_arraymap(this.groups);
        return this.groups;
    }
    async updateMemberships() {
        const members = (await request(`courses/${this.external_id}/memberships`)) as Membership[];
        console.log('groups', this.groups, 'members', members);
        this.groups.forEach((g) => (g.members = []));
        this.users.forEach((u) => (u.groups = []));
        members.forEach((m) => {
            const g = this.groupsById[m.group_id];
            const u = this.usersById[m.user_id];
            g.members.push({
                id: m.user_id,
                slug: u.canvas_username,
                lastname: u.lastname,
                firstname: u.firstname,
                role: m.role,
                join_model: m.join_model,
            });
            u.groups.push(g);
        });
    }
}
