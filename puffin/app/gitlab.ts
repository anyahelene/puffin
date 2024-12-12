import { html, render } from 'uhtml';
import { busy_event_handler, get_gitlab_project } from './puffin';
import { BorbPanel } from 'puffin/borb/Frames';
import { Course, Project, GitlabProject } from './model';
import { GITLAB_PATH_RE, GITLAB_PREFIX, form_field } from './forms';


type pick_project_form_data = {
    _error?: string;
    _project_ref?: string;
    course?: Course;
    gitlab_id?: number;
    description?: string;
    name?: string;
    slug?: string;
    project?: GitlabProject;
};
export async function pick_project_form(
    data: pick_project_form_data,
    title: string,
    panel: HTMLElement,
    partial = false,
): Promise<pick_project_form_data> {
    return new Promise((resolve, reject) => {
        let disable_input = false;
        const get_gitlab_proj = busy_event_handler(
            async (ev) => {
                const elt = panel.querySelector('#select_project') as HTMLInputElement;
                if (disable_input) {
                    disable_input = false;
                    show_form();
                    return;
                }
                data._project_ref = elt.value;
                data._error = undefined;
                try {
                    const proj = await get_gitlab_project(
                        data.course?.external_id,
                        data._project_ref,
                    );
                    data.gitlab_id = proj.id;
                    data.description = proj.description;
                    data.name = proj.name;
                    data.slug = proj.path_with_namespace;
                    data.project = proj;
                } catch (e) {
                    data._error = e.userMessage;
                }
                if (data._error || !data.gitlab_id) {
                    show_form();
                } else if (partial) {
                    if (data._error || !data.gitlab_id) {
                        disable_input = false;
                    } else {
                        elt.value = data.slug;
                        disable_input = true;
                    }
                    show_form();
                } else {
                    render(panel, html``);
                    resolve(data);
                }
            },
            () => {},
        );
        const get_gitlab_proj_cancel = () => {
            render(panel, html``);
            reject('Cancelled');
        };

        const cancel_edit = () => {
            const elt = panel.querySelector('#select_project') as HTMLInputElement;
            elt.value = data._project_ref;
            disable_input = true;
            show_form();
        };
        const show_form = () => {
            console.log('show_form', data);
            const project_input = html`<label for="select_project">Gitlab project:</label>
                <input
                    type="text"
                    id="select_project"
                    name="project_ref"
                    .disabled=${disable_input}
                    placeholder="URL or path or project id"
                    value=${data._project_ref || ''}
                />
                ${data._error ? '❌' : data.gitlab_id ? '✔️' : ''}`;
            if (partial) {
                render(
                    panel,
                    html`
                        ${project_input}
                        <div class="buttons">
                            <button type="button" onclick=${get_gitlab_proj}
                                >${disable_input ? 'Edit' : 'Ok'}</button
                            >
                            ${disable_input || !data._project_ref
                                ? ''
                                : html` <button type="button" onclick=${cancel_edit}
                                      >Cancel</button
                                  >`}
                        </div>
                        ${data._error ? html`<div class="error">${data._error}</div>` : ''}
                    `,
                );
            } else {
                render(
                    panel,
                    html`
                        <form>
                            ${project_input}
                            <div class="buttons">
                                <button
                                    type="button"
                                    id="select_project_from"
                                    onclick=${get_gitlab_proj}
                                    >${title}</button
                                >
                                <button type="button" id="foobar" onclick=${get_gitlab_proj_cancel}
                                    >Cancel</button
                                >
                            </div>
                            ${data._error ? html`<div class="error">${data._error}</div>` : ''}
                        </form>
                    `,
                );
            }
        };
        show_form();
    });
}

export function project_field(data: Record<string, any>, redraw: () => void) {
    const check_gitlab = (data: any) => {
        return busy_event_handler(async (ev: MouseEvent) => {
            console.log('check_gitlab', data, JSON.stringify(data.obj));
            if (data.obj[`_${data.field}_path`] === undefined) {
                data.obj[`_${data.field}_project`] = data.obj[`${data.field}_project`];
                data.obj[`_${data.field}_path`] =
                    data.obj[`${data.field}_project`]?.path_with_namespace || '';
                data.obj[`${data.field}_project`] = undefined;
                console.warn("1: ", JSON.stringify(data.obj));
            } else if (data.ref?.current?.value) {
                const p = await get_gitlab_project(
                    data.obj.course?.external_id,
                    data.ref.current.value,
                );
                console.log('get_gitlab_project→', p);
                data.obj[`${data.field}_project`] = p;
                data.obj[`_${data.field}_path`] = undefined;
                if(data.on_valid_project)
                    data.on_valid_project(p);
                console.log("2: ", JSON.stringify(data.obj));
            } else {
                data.obj[`${data.field}_project`] = undefined;
                data.obj[`_${data.field}_path`] = undefined;
                console.log("3: ", JSON.stringify(data.obj));
            }
        }, redraw);
    };

    const cancel_gitlab = (data) => {
        return busy_event_handler(async (ev: MouseEvent) => {
            console.log('cancel_gitlab', data.ref, data.field, data);
            data.obj[`${data.field}_project`] = data.obj[`_${data.field}_project`];
            data.obj[`_${data.field}_path`] = undefined;
        }, redraw);
    };
    const change_gitlab = (ev: MouseEvent, elt: HTMLInputElement, obj, data) => {
        console.log('change_gitlab', data.field);
        obj[`_${data.field}_path`] = elt.value;
    };
    data.editable = data.obj[`_${data.field}_path`] !== undefined || data.obj[`${data.field}_project`] === undefined;
    data.pattern = `^${GITLAB_PATH_RE}(/${GITLAB_PATH_RE})*$`;
    data.value =
        data.obj[`_${data.field}_path`] !== undefined
            ? data.obj[`_${data.field}_path`]
            : data.obj[`${data.field}_project`]?.path_with_namespace || '';
    data.link_prefix = data.obj[`_${data.field}_path`] !== undefined ? undefined : GITLAB_PREFIX;
    data.onchange = change_gitlab;
    data.button_make_onclick = check_gitlab;
    data.button2_make_onclick = cancel_gitlab;
    data.button_title =
        data.obj[`_${data.field}_path`] !== undefined ? 'Ok' : data.obj[`${data.field}_project`] ? 'Change' : 'Add';
    data.button2_title = data.obj[`_${data.field}_path`] !== undefined ? 'Cancel' : undefined;
    return form_field(data);
}
