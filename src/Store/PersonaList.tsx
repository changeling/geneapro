import { actionCreator } from "../Store/Actions";
import { WHITE } from "../Store/ColorTheme";
import * as GP_JSON from "../Server/JSON";

export interface PersonaListSettings {
   colors: GP_JSON.ColorSchemeId;
   filter: string;
}

export const defaultPersonaList: PersonaListSettings = {
   colors: WHITE.id,
   filter: '',
};

/**
 * Action: change one or more settings
 */
export const changePersonaListSettings = actionCreator<{
   diff: Partial<PersonaListSettings>;
}>("PERSONALIST/SETTINGS");
