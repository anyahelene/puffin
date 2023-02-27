import { display_panel, request, to_table } from './puffin';
import { Course, Course_user, User_account, User, Group, Membership } from './model';
import { BorbPanelBuilder } from '../borb/Frames';
import { html, render } from 'uhtml';

function to_arraymap<T extends { id: number }>(array: T[]) {
    const arraymap: T[] = [];
    array.forEach((v, i) => {
        arraymap[v.id] = v;
    });
    return arraymap;
}
type CourseUserAccount = Course_user & User_account & { groups?: Group[] };
let foo: CourseUserAccount;
type Member = {
    id: number;
    slug: string;
    firstname: string;
    lastname: string;
    role: string;
    join_model: string;
};
type GroupWithMembers = Group & { members: Member[] };
class _courses {
    public current?: Course = null;
    public users: CourseUserAccount[] = [];
    public groups: GroupWithMembers[] = [];
    public courses: Course[] = [];

    async sync(course_id: number,{sync_canvas = true, sync_gitlab = true, sync_groups = true, feedback=(msg:string) => null}) {
        let result;
        let updates = 0;
        if (sync_canvas) {
            feedback(`[${updates}] syncing canvas…`);
            result = await request(`courses/${course_id}/sync?sync_canvas=true`, 'POST');
            updates += result.length;
            console.log('canvas_sync result:', result);
        }
        if (sync_gitlab) {
            feedback(`[${updates}] syncing gitlab…`);
            result = await request(`courses/${course_id}/sync?sync_gitlab=true`, 'POST');
            updates += result.length;
            feedback(`Updated ${result.length} records`);
            console.log('gitlab_sync result:', result);
        }
        if (sync_groups) {
            feedback(`[${updates}] syncing groups…`);
            result = await request(`courses/${course_id}/sync?sync_canvas_groups=true`, 'POST');
            updates += result.length;
            feedback(`Updated ${result.length} records`);
            console.log('groups_sync result:', result);
        }
        if (Courses.current?.external_id === course_id) {
            feedback(`[${updates}] syncing view…`);
            // reload everything
            updates += result.length;
            await set_active_course(course_id);
            set_course_view();
        }
        feedback('');
    }
}
export const Courses = new _courses();

export async function add_course() {
    const canvas_courses: Record<string, any>[] = await request('courses/canvas');
    const now = new Date();
    canvas_courses.forEach((course) => {
        course.start_at = new Date(course.start_at);
        course.end_at = new Date(course.end_at);
        if (course.end_at < now) course.workflow_state = 'finished';
    });
    canvas_courses.sort((a, b) => b.start_at - a.start_at);
    document.getElementById('display').replaceChildren(...to_table(canvas_courses));
}

export async function set_active_course(course_id: number): Promise<Course> {
    if (!Courses.courses[course_id]) {
        Courses.courses[course_id] = await request(`courses/${course_id}`);
    }
    Courses.current = Courses.courses[course_id];
    Courses.users = to_arraymap(
        (await request(`courses/${course_id}/users?accounts=true`)) as CourseUserAccount[],
    );
    Courses.groups = to_arraymap(
        (await request(`courses/${course_id}/groups`)) as GroupWithMembers[],
    );
    const members = (await request(`courses/${course_id}/memberships`)) as Membership[];
    console.log('groups', Courses.groups, 'members', members);
    Courses.groups.forEach((g) => (g.members = []));
    Courses.users.forEach((u) => (u.groups = []));
    members.forEach((m) => {
        const g = Courses.groups[m.group_id];
        const u = Courses.users[m.user_id];
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
    return Courses.current;
}

export function display_course(course: Course) {
    const panel = new BorbPanelBuilder()
        .frame('frame2')
        .panel('div', course.slug)
        .title(course.slug)
        .select()
        .done();
    console.log(panel, course);
    render(panel, html`<h1>${course.name}</h1>`);
}
export function set_course_view() {
    display_course(Courses.current);
    const group_table = to_table({ _type: 'group,with_member_list[]', data: Courses.groups });
    const user_table = to_table({ _type: 'course_user,with_group_list[]', data: Courses.users });
    const user_panel = new BorbPanelBuilder()
        .frame('frame3')
        .panel('borb-sheet', 'course_users')
        .title('Users')
        .select()
        .done();
    user_panel.replaceChildren(...user_table);
    const group_panel = new BorbPanelBuilder()
        .frame('frame3')
        .panel('borb-sheet', 'course_groups')
        .title('Groups')
        .done();
    group_panel.replaceChildren(...group_table);
}
