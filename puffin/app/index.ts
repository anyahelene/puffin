import {
    MDRender,
    SubSystem,
    Borb,
    Buttons,
    Frames,
    Settings,
    Sheet,
    History,
    Terminals,
} from '../borb';
import { BorbFrame, BorbPanelBuilder } from '../borb/Frames';
import nearley from 'nearley';
import grammar from '../qlang/qlang.ne';

import { TilingWM, TilingWindow } from '../borb/TilingWM';
import { html, render } from 'uhtml';
//import defaultConfig from './config.json';
const defaultConfig = {};
import {
    puffin,
    csrf_token,
    display_panel,
    login_panel,
    request,
    to_table,
    updateToken,
    get_gitlab_group,
    get_gitlab_project,
    create_team_from_project_url,
    gitlab_url,
} from './puffin';
import { Course, SelfUser, tables } from './model';
import { CourseView } from './courses';
import { add_assignment_form, edit_assignment_form } from './assignments';
import { pick_project_form } from './gitlab';
import { add_many_teams_form, add_team_form } from './teams';
import moo from 'moo';
import slugify from 'slugify';
slugify.extend({ '+': '-' });
puffin.tables = tables;
puffin.Course = Course;
puffin.CourseView = CourseView;
puffin.SubSystem = SubSystem;
puffin.Borb = Borb;
puffin.add_assignment_form = add_assignment_form;
puffin.edit_assignment_form = edit_assignment_form;
puffin.get_gitlab_group = get_gitlab_group;
puffin.get_gitlab_project = get_gitlab_project;
puffin.create_team_from_project_url = create_team_from_project_url;
puffin.login_panel = login_panel;
puffin.pick_project_form = pick_project_form;
puffin.add_team_form = add_team_form;
puffin.add_many_teams_form = add_many_teams_form;
window['puffin'] = puffin;
SubSystem.setup(puffin, {
    proxy: true,
    hotReload: !!import.meta.webpackHot,
    global: true,
});
SubSystem.waitFor(Settings).then((settings) => {
    console.warn('CONFIGS:', settings.configs);
    settings.configs[4] = defaultConfig;
});

const layoutPrefs = {
    /*    frame1: {
        width: 12,
        height: 6,
        iconified: false,
        maximized: false,
    },*/
    frame2: {
        width: 32,
        height: 8,
        iconified: false,
        maximized: false,
    },
    frame3: {
        width: 32,
        height: 8,
        iconified: false,
        maximized: false,
    },
};
const layoutSpec = {
    size: 32,
    dir: 'H',
    items: [
        {
            size: 16,
            dir: 'V',
            max_container: true,
            items: [
                {
                    size: 8,
                    item: 'frame2',
                },
                /*              {
                    size: 9,
                    dir: 'H',
                    items: [
                        {
                            size: 0,
                            item: 'frame1',
                        },
                        {
                            size: 14,
                            item: 'frame2',
                        },
                    ],
                },*/
                {
                    size: 8,
                    item: 'frame3',
                },
            ],
        },
    ],
};
interface TilingWM {
    initialize: (spec: object, prefs: object) => void;
}
puffin.TilingWM = TilingWM;
puffin.TilingWindow = TilingWindow;
console.log('Hello!!');
const wm = new TilingWM('mid', 32, 16);
puffin.wm = wm;
window.addEventListener('DOMContentLoaded', (ev) => {
    wm.initialize(layoutSpec, layoutPrefs);
});
puffin.courses = CourseView;
puffin.to_table = to_table;
//SubSystem.waitFor(Frames.Frames).then((frames) => {
puffin.display_panel = display_panel;
//});
puffin.nearley = nearley;
puffin.grammar = grammar;
puffin.parser = new nearley.Parser(nearley.Grammar.fromCompiled(grammar));
puffin.request = request;
let reqId = 0;
const resultElt = document.getElementById('resultElt');
const anchor = document.getElementById('anchor');
const idField = document.getElementById('id') as HTMLInputElement;
const dataField = document.getElementById('data') as HTMLInputElement;
const submitBtn = document.getElementById('submit');

async function submit(method: string) {
    const endpoint = idField.value;
    const requestBody = dataField.value ? JSON.parse(dataField.value) : undefined;
    console.log('submit', endpoint, requestBody);
    const result = await request(endpoint, method, requestBody);
    console.log('result', result);
    resultElt.replaceChildren(...to_table(result));
}

interface Group {
    group_id: number;
    group_slug: string;
}

const DATA = {
    groups: [] as Group[],
};

function enterPressed(ev: KeyboardEvent) {
    if (ev.key === 'Enter') {
        submit('GET');
    }
}
idField.addEventListener('keydown', enterPressed);
document.getElementById('get').addEventListener('click', (e) => submit('GET'));
document.getElementById('put').addEventListener('click', (e) => submit('PUT'));
document.getElementById('post').addEventListener('click', (e) => submit('POST'));
document.getElementById('patch').addEventListener('click', (e) => submit('PATCH'));

SubSystem.waitFor('dom').then(() => {
    if (window.location.search) {
        const usp = new URLSearchParams(window.location.search);
        if (usp.has('course')) {
            Course.setActiveCourse(parseInt(usp.get('course'))).then(() =>
                CourseView.set_course_view(),
            );
        }
    }

    request('users/self', 'GET', undefined, false, true).then(async (self: SelfUser) => {
        if (self?.login_required) {
            const path = window.location.pathname.replace(/[^/]*$/, '');
            window.location.replace(`${path}login/gitlab?next=${window.location.pathname}`);
            return;
        }
        puffin.self = self;
        Course.current_user = self;
        const user_info = document.getElementById('user-info');
        self.on_update = () => {
            render(
                user_info,
                html`
                    <span class="name" title=${self.course_user?.role || ''}
                        >${self.firstname} ${self.lastname}</span
                    >
                    <ul class="account-status">
                        <li
                            data-account="canvas"
                            data-account-short="C"
                            data-account-name="Canvas"
                            ?data-is-active=${!!self.canvas_account}
                        ></li>
                        <li
                            data-account="gitlab"
                            data-account-short="G"
                            data-account-name="GitLab"
                            ?data-is-active=${!!self.gitlab_account}
                        ></li>
                        <li
                            data-account="discord"
                            data-account-short="D"
                            data-account-name="Discord"
                            ?data-is-active=${!!self.discord_account}
                        ></li>
                    </ul>
                    ${self.is_admin
                        ? html`<span class="is-admin" title="Logged in as administrator"
                              ><span></span
                          ></span>`
                        : ''}
                `,
            );
        };
        await Course.updateCourses();
        try {
            await Course.setActiveCourse(45714);
        } catch (e) {
            console.error('Failed to set active course', e);
        }
        if (self.is_admin) {
            puffin.debug['console'] = true;
            document
                .querySelectorAll('#frame3 [hidden=true]')
                .forEach((p) => p.removeAttribute('hidden'));
            (document.querySelector('#frame3') as BorbFrame).queueUpdate(true);
            CourseView.set_course_view();
        } else {
            const user = Course.current.usersById[self.id];
            const team = user.team[0];
            console.log('non-admin user: ', user, team);
            const debug = puffin.debug['console'] ? html`<div><button type="button" onclick=${() => console.log(this)}>Debug</button></div>` : '';
            const user_panel = new BorbPanelBuilder()
                .frame('frame2')
                .panel('div', 'user_panel')
                .title(`${user.firstname} ${user.lastname}`)
                .select()
                .done();
            render(
                user_panel,
                html`<h2>${user.firstname} ${user.lastname}</h2>
                 <b>Team:</b><a href="${gitlab_url(team.json_data.project_path)}" target="_blank"
                  > ${team.json_data.project_name} – [${team.json_data.project_path}]</a>
                  ${debug}`,
            );
            const team_panel = new BorbPanelBuilder()
                .frame('frame3')
                .panel('div', 'team_panel')
                .title(team.name)
                .select()
                .done();
            team.display(team_panel);
        }
    });

    const retro = (ev) => {
        document.querySelector('body').classList.toggle('retro');
    };
    document
        .querySelector('#page-home')
        .appendChild(
            html.node`<input id="retro" onchange=${retro} type="checkbox" /><label for="retro">Go 8-bit</label>`,
        );
});
import '../borb/css/frames.scss';
import '../borb/css/buttons.scss';
import '../borb/css/common.scss';
import '../borb/css/markdown.scss';
import '../borb/css/terminal.scss';
import '../borb/css/editor.scss';
import '../borb/css/sheet.scss';
import '../css/style.scss';
import { pick } from 'lodash-es';
//import styles from '../css/common.scss';
//console.log(styles)

if (import.meta.webpackHot) {
    console.warn('WebpackHot enabled');
    //turtleduck.webpackHot = import.meta.webpackHot;
    import.meta.webpackHot.accept(
        [
            '../borb/css/frames.scss',
            '../borb/css/buttons.scss',
            '../borb/css/common.scss',
            '../borb/css/markdown.scss',
            '../borb/css/terminal.scss',
            '../borb/css/editor.scss',
        ],
        function (outdated) {
            outdated.forEach((dep) => {
                console.log(dep);
                //turtleduck.styles.update(dep.replace('./', '').replace('.scss', '.css'));
            });
        },
        (err, context) => {
            console.error('HMR failed:', err, context);
        },
    );

    //  import.meta.webpackHot.accept('./css/frames.scss?raw', function (...args) {
    //		console.warn("frames", args);
    //	});
}
