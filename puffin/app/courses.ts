import {
    busy_event_handler,
    display_panel,
    get_gitlab_group,
    get_gitlab_project,
    request,
    to_table,
    puffin,
} from './puffin';
import { Course } from './model';
import { BorbPanelBuilder } from '../borb/Frames';
import { html, render } from 'uhtml';
import slugify from 'slugify';
import { form_field, form_select, GITLAB_PATH_RE, GITLAB_PREFIX } from './forms';
import { update } from 'puffin/borb/Styles';
import { placeholder } from '@codemirror/view';

class _courses {
    _course_selector: HTMLSelectElement;

    async sync(
        course_id: number,
        {
            sync_canvas = true,
            sync_gitlab = true,
            sync_groups = true,
            feedback = (msg: string) => null,
        },
    ) {
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
        if (Course.current?.external_id === course_id) {
            feedback(`[${updates}] syncing view…`);
            // reload everything
            updates += result.length;
            await Course.current.setActive();
            CourseView.set_course_view();
        }
        feedback('');
    }

    get_course_panel(course: Course, select = true) {
        return new BorbPanelBuilder()
            .frame('frame2')
            .panel('div', course ? course.slug : 'new')
            .title(course ? course.slug : 'New course')
            .select(select)
            .done();
    }
    edit_course(course: Course, editable = true, select = true) {
        const panel = this.get_course_panel(course, select);

        const edit = (ev) => {
            editable = true;
            course.clear_log();
            redraw();
        };
        const save = busy_event_handler(
            async (ev) => {
                editable = false;
                //course.slug = slugify(course.name);
                if (!course._gitlab_path) course.json_data['gitlab_path'] = course._gitlab_path;
                if (course._gitlab_path !== course.json_data['gitlab_path']) {
                    const g = await get_gitlab_group(undefined, course._gitlab_path);
                    if (g) course.json_data['gitlab_path'] = course._gitlab_path = g.full_path;
                }
                if (!course._gitlab_student_path)
                    course.json_data['gitlab_student_path'] = course._gitlab_student_path;
                if (course._gitlab_student_path !== course.json_data['gitlab_student_path']) {
                    const g = await get_gitlab_group(undefined, course._gitlab_student_path);
                    if (g)
                        course.json_data['gitlab_student_path'] = course._gitlab_student_path =
                            g.full_path;
                }
                await request(`courses/${course.external_id}/`, 'PUT', {
                    name: course.name,
                    slug: course.slug,
                    expiry_date: course.expiry_date,
                    gitlab_path: course.json_data['gitlab_path'],
                    gitlab_student_path: course.json_data['gitlab_student_path'],
                });
                course.log('Changes saved');
                await course.updateCourse();
            },
            () => redraw(),
            course,
        );
        const cancel = busy_event_handler(
            async (ev) => {
                editable = false;
                await course.updateCourse();
            },
            () => redraw(),
            course,
        );
        const reset = busy_event_handler(
            async (ev) => {
                const canvasdata = await request(`courses/${course.external_id}/?from_canvas=true`);
                if (canvasdata) {
                    course.name = canvasdata.name;
                    course.slug = canvasdata.slug;
                    course.expiry_date = canvasdata.end_at;
                    course.log('Refreshed from Canvas');
                }
            },
            () => redraw(),
            course,
        );
        type gitlab_getter = (course: Course | number, ref: string) => Promise<Record<string, any>>;
        const check_gitlab = (f: gitlab_getter) => (data: any, value?: any) => {
            return busy_event_handler(
                async (ev: MouseEvent) => {
                    if (data.ref?.current?.value || value) {
                        const g = await f(undefined, data.ref?.current?.value || value);
                        if (g) {
                            data.ref.current.value =
                                course[data.field] =
                                course.json_data[data.field.replace(/^_/, '')] =
                                    g.full_path;
                        } else {
                            console.warn('not found', g);
                        }
                    }
                },
                redraw,
                course,
                [data.ref],
            );
        };
        const check_gitlab_group = check_gitlab(get_gitlab_group);
        const check_gitlab_project = check_gitlab(get_gitlab_project);
        const sync_all = (ev: MouseEvent) => {
            const target = ev.target as HTMLButtonElement;
            const feedback = (s: string) => {
                if (s) {
                    target.innerText = s;
                    target.disabled = false;
                    target.classList.add('running');
                }
            };
            ev.preventDefault();
            CourseView.sync(course.external_id, { feedback })
                .then(() => {
                    target.innerText = target.dataset.text;
                    target.disabled = false;
                    target.classList.remove('running');
                })
                .catch((reason) => {
                    target.innerText = `Sync failed: ${reason}`;
                    target.disabled = false;
                    target.classList.remove('running');
                });
        };
        panel.classList.add('form');
        const redraw = () =>
            render(
                panel,
                html`
                    ${form_field({
                        editable,
                        obj: course,
                        name: 'Name',
                        field: 'name',
                        required: true,
                    })}
                    ${form_field({
                        editable,
                        obj: course,
                        name: 'Canvas course',
                        type: 'number',
                        field: 'external_id',
                        required: true,
                        disabled: course.external_id !== 0,
                    })}
                    ${form_field({
                        editable,
                        obj: course,
                        pattern: `^${GITLAB_PATH_RE}(/${GITLAB_PATH_RE})*$`,
                        name: 'Gitlab group',
                        field: '_gitlab_path',
                        recommended: '$COURSE_CODE/$COURSE_TERM',
                        link_prefix: course.has_valid_gitlab_path() ? GITLAB_PREFIX : undefined,
                        button_make_onclick: check_gitlab_group,
                        button_class: course.has_valid_gitlab_path() ? 'check-ok' : 'check-unknown',
                        button_title: editable ? 'Check' : 'Check default',
                    })}
                    ${form_field({
                        editable,
                        obj: course,
                        pattern: `^${GITLAB_PATH_RE}(/${GITLAB_PATH_RE})*$`,
                        name: 'Gitlab wiki',
                        field: '_gitlab_wiki',
                        recommended: '$GITLAB_GROUP/' + course.slug,
                        link_prefix: course.has_valid_gitlab_path() ? GITLAB_PREFIX : undefined,
                        button_make_onclick: check_gitlab_project,
                        button_class: course.has_valid_gitlab_path() ? 'check-ok' : 'check-unknown',
                        button_title: editable ? 'Check' : 'Check default',
                    })}
                    ${form_field({
                        editable,
                        obj: course,
                        pattern: `^${GITLAB_PATH_RE}(/${GITLAB_PATH_RE})*$`,
                        name: 'Fork assignments to',
                        field: '_gitlab_student_path',
                        recommended: '$GITLAB_GROUP/$ASGN_SHORTNAME/$GITLAB_USERNAME\\_$ASGN_SLUG',
                        link_prefix: course.has_valid_gitlab_student_path()
                            ? GITLAB_PREFIX
                            : undefined,
                        button_make_onclick: check_gitlab_group,
                        button_class: course.has_valid_gitlab_student_path()
                            ? 'check-ok'
                            : 'check-unknown',
                        button_title: editable ? 'Check' : undefined,
                    })}
                    <div class="form-control">
                        <button type="button" onclick=${cancel} ?disabled=${!editable}
                            >❌ Cancel Edit</button
                        >
                        <button type="button" onclick=${reset} ?disabled=${!editable}
                            >🏫 Reset to Canvas defaults</button
                        >
                    </div>
                    <div class="form-control">
                        <button type="button" onclick=${editable ? save : edit}
                            >${editable
                                ? '💾 Save Course Settings'
                                : '🖊️ Edit Course Settings'}</button
                        >
                    </div>
                    <div class="form-control">
                        <button type="button" data-text="Sync course data" onclick=${sync_all}
                            >Sync course data</button
                        ></div
                    >
                    <div
                        ><a
                            href=${`courses/${course.external_id}/users/?details=true&csv=true`}
                            target="_blank"
                            >Users as CSV</a
                        ></div
                    >
                    <div> ${to_table({ _type: 'Assignment[]', data: course.assignments })} </div>
                    <div class="log">
                        ${course._log.map(
                            (entry) => html`<li class=${entry[0]}>${entry[1]}</li>`,
                        ) || ''}</div
                    >
                `,
            );
        redraw();
    }
    display_course(course: Course, select = true) {
        const panel = this.get_course_panel(course, select);
        console.log(panel, this);

        render(
            panel,
            html`
                <h1>${course.name}</h1>
                <div class="buttons"> </div>
            `,
        );
    }

    async add_course(canvas_courses?: Record<string, any>[], canvas_id?: number) {
        if (!canvas_courses) {
            const panel = this.get_course_panel(null);
            // render(panel, html`Loading course list from Canvas...`);
            canvas_courses = await request('courses/canvas');
            const now = new Date();
            canvas_courses.forEach((course) => {
                course.start_at = new Date(course.start_at);
                course.end_at = new Date(course.end_at);
                if (course.end_at < now) course.workflow_state = 'finished';
                console.log(course.canvas_id, typeof course.canvas_id);
            });
            canvas_courses.sort((a, b) => b.start_at - a.start_at);
            render(
                panel,
                html`<table>
                    <thead>
                        <tr
                            ><th>Term</th><th>Slug</th><th>Name</th><th>Canvas Id</th><th>State</th
                            ><th></th
                        ></tr>
                    </thead>
                    <tbody>
                        ${canvas_courses.map(
                            (course) => html`<tr
                                data-id=${course.canvas_id}
                                class=${course.workflow_state == 'finished' ? 'disabled' : ''}
                            >
                                <td>${course.term}</td>
                                <td>${course.slug}</td>
                                <td>${course.name}</td>
                                <td>${course.canvas_id}</td>
                                <td>${course.workflow_state}</td>
                                <td
                                    ><button
                                        type="button"
                                        onclick=${() =>
                                            this.add_course(canvas_courses, course.canvas_id)}
                                        >Add course</button
                                    ></td
                                >
                            </tr>`,
                        )}
                    </tbody>
                </table>`,
            );
        }
        if (canvas_id) {
            const course = canvas_courses.find((course) => course.id === canvas_id);
            console.log('add_course payload:', course);
            if (course) {
                const result = await request('courses/', 'POST', course);
                console.log('add_course result:', result);
                await Course.updateCourses();
                await Course.setActiveCourse(canvas_id);
                CourseView.set_course_view(true);
            } else {
                // ERROR
            }
        }
        return canvas_courses;
    }

    set_course_view(select = true) {
        this.refresh(true, select);
    }

    refresh(setView = false, select = false) {
        const course = Course.current;
        if (course) {
            CourseView.edit_course(course, false, select);

            if (setView) puffin.currentView = this;
            this.open_user_list(select);
            this.open_group_list(false);
            this.open_team_list(false);
        }
    }

    open_user_list(select = false) {
        const course = Course.current;
        const user_table = to_table({
            _type: 'FullUser[]',
            data: course.users,
        });
        const user_panel = new BorbPanelBuilder()
            .frame('frame3')
            .panel('borb-sheet', 'course_users')
            .title('Users')
            .select(select)
            .done();
        user_panel.replaceChildren(...user_table);
    }
    open_group_list(select = false) {
        const course = Course.current;
        const group_table = to_table({ _type: 'Group[]', data: course.groups });
        const group_panel = new BorbPanelBuilder()
            .frame('frame3')
            .panel('borb-sheet', 'course_groups')
            .title('Groups')
            .select(select)
            .done();
        group_panel.replaceChildren(...group_table);
    }
    open_team_list(select = false) {
        const course = Course.current;
        const team_table = to_table({
            _type: 'Team[]',
            data: course.groups.filter((g) => g.kind === 'team'),
        });
        const team_panel = new BorbPanelBuilder()
            .frame('frame3')
            .panel('borb-sheet', 'course_teams')
            .title('Teams')
            .select(select)
            .done();
        team_panel.replaceChildren(...team_table);
    }

    update_course_list() {
        const elt = document.getElementById('course-info');
        const obj = { course: Course.current?.external_id || 0 };
        const change_course = async (ev: MouseEvent, elt: HTMLSelectElement) => {
            if (elt.value === 'new') {
                CourseView.add_course();
                this.update_course_list();
            } else if (elt.value) {
                const course = Course.courses[parseInt(elt.value)];
                if (course) {
                    await course.setActive(true);
                    CourseView.refresh(true, true);
                }
            }
        };
        const alternatives = Course.courses.map((c) => [c.external_id, c.name]);
        alternatives.push(['new', 'Add New...']);
        render(
            elt,
            form_select({
                editable: true,
                obj,
                name: 'Course',
                field: 'course',
                onchange: change_course,
                output: (e: HTMLSelectElement) => {
                    this._course_selector = e;
                },
                value: Course.current?.external_id || 0,
                alternatives,
            }),
        );
    }
    on_course_change(course: Course) {
        if (this._course_selector) this._course_selector.value = `${course.external_id}`;
    }
}
export const CourseView = new _courses();
