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

class _courses {
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
            () => redraw(), course
        );
        const cancel = busy_event_handler(
            async (ev) => {
                editable = false;
                await course.updateCourse();
            },
            () => redraw(), course
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
            () => redraw(),course,
        );
        const check_gitlab = (data: any) => {
            return busy_event_handler(
                async (ev: MouseEvent) => {
                    if (data.ref?.current?.value) {
                        const g = await get_gitlab_group(undefined, data.ref.current.value);
                        if (g) {
                            data.ref.current.value =
                                course[data.field] =
                                course.json_data[data.field.replace(/^_/, '')] =
                                    g.full_path;
                        }
                    }
                },
                redraw, course,
                [data.ref],
            );
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
                        name: 'Gitlab path',
                        field: '_gitlab_path',
                        link_prefix: course.has_valid_gitlab_path() ? GITLAB_PREFIX : undefined,
                        button_make_onclick: check_gitlab,
                        button_class: course.has_valid_gitlab_path() ? 'check-ok' : 'check-unknown',
                        button_title: editable ? 'Check' : undefined,
                    })}
                    ${form_field({
                        editable,
                        obj: course,
                        pattern: `^${GITLAB_PATH_RE}(/${GITLAB_PATH_RE})*$`,
                        name: 'Gitlab student path',
                        field: '_gitlab_student_path',
                        link_prefix: course.has_valid_gitlab_student_path()
                            ? GITLAB_PREFIX
                            : undefined,
                        button_make_onclick: check_gitlab,
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
                        > </div
                    ><div class="form-control">
                        <button type="button" onclick=${editable ? save : edit}
                            >${editable
                                ? '💾 Save Course Settings'
                                : '🖊️ Edit Course Settings'}</button
                        > </div
                    ><div class="log">
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
        const sync_all = (ev: MouseEvent) => {
            const target = ev.target as HTMLButtonElement;
            const feedback = (s: string) => {
                if (s) {
                    target.innerText = s;
                    target.disabled = true;
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
        render(
            panel,
            html`
                <h1>${course.name}</h1>
                <div class="buttons">
                    <button type="button" data-text="Sync course data" onclick=${sync_all}
                        >Sync course data</button
                    >
                </div>
            `,
        );
    }

    async add_course() {
        const panel = this.get_course_panel(null);
        const canvas_courses: Record<string, any>[] = await request('courses/canvas');
        const now = new Date();
        canvas_courses.forEach((course) => {
            course.start_at = new Date(course.start_at);
            course.end_at = new Date(course.end_at);
            if (course.end_at < now) course.workflow_state = 'finished';
        });
        canvas_courses.sort((a, b) => b.start_at - a.start_at);
        panel.replaceChildren(...to_table(canvas_courses));
    }

    set_course_view(select = true) {
        this.refresh(true, select)
    }

    refresh(setView = false, select = false) {
        const course = Course.current;
        if (course) {
            CourseView.edit_course(course, false, select);
            const group_table = to_table({ _type: 'Group[]', data: course.groups });
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
            const group_panel = new BorbPanelBuilder()
                .frame('frame3')
                .panel('borb-sheet', 'course_groups')
                .title('Groups')
                .done();
            group_panel.replaceChildren(...group_table);
            if(setView)
                puffin.currentView = this;
        }
    }

    update_course_list() {
        const elt = document.getElementById('course-info');
        const obj = { course: Course.current?.name };
        const change_course = (ev: MouseEvent, elt: HTMLInputElement) => {
            if (elt.value) {
                const course = Course.courses[parseInt(elt.value)];
                if (course) course.setActive();
            }
        };

        render(
            elt,
            form_select({
                editable: true,
                obj,
                name: 'Course',
                field: 'course',
                default: Course.current?.name || 0,
                alternatives: Course.courses.map((c) => [c.external_id, c.name]),
            }),
        );
    }
}
export const CourseView = new _courses();
