import * as Redux from "redux";
import { REHYDRATE } from "redux-persist/constants";
import { FanchartSettings } from "../Store/Fanchart";
import { PedigreeSettings } from "../Store/Pedigree";
import { RadialSettings } from "../Store/Radial";
import { QuiltsSettings } from "../Store/Quilts";
import { Person, PersonSet } from "../Store/Person";
import { SourceSet, SourceListSettings } from "../Store/Source";
import { PlaceListSettings } from '../Store/Place';
import { HistoryItem } from "../Store/History";
import { actionCreator } from "../Store/Actions";
import { predefinedThemes } from "../Store/ColorTheme";
import { GenealogyEventSet } from "../Store/Event";
import { PersonaListSettings } from "../Store/PersonaList";
import { PlaceSet } from "../Store/Place";
import { ResearcherSet } from "../Store/Researcher";
import { StatsSettings } from "../Store/Stats";
import * as GP_JSON from "../Server/JSON";

export interface MetadataDict extends GP_JSON.Metadata {
   p2p_types_dict: {[id: number]: GP_JSON.P2PType};
   event_type_roles_dict: {[id: number]: GP_JSON.EventTypeRole};
   researchers_dict: {[id: number]: GP_JSON.Researcher};
   char_part_types_dict: {[id: number]: GP_JSON.CharacteristicPartType};
   char_part_SEX: number;  // the one corresponding to 'sex'
}

export interface AppState {
   fanchart: FanchartSettings;
   history: HistoryItem[]; // id of persons recently visited
   pedigree: PedigreeSettings;
   personalist: PersonaListSettings;
   placelist: PlaceListSettings;
   quilts: QuiltsSettings;
   radial: RadialSettings;
   sourcelist: SourceListSettings;
   stats: StatsSettings;

   metadata: MetadataDict;

   // ??? Those should be replaced with local data in the various views, to
   // reduce long-term memory usage. The caching is not really useful, since
   // views are fetching them anyway.
   persons: PersonSet; // details for all persons
   places: PlaceSet; // details for all places
   events: GenealogyEventSet; // all known events
   sources: SourceSet;
}

export type GPDispatch = Redux.Dispatch<AppState>;
export type GPStore = Redux.Store<AppState>;

/**
 * Given an id, returns the name of the corresponding theme.
 */
export const themeNameGetter = (s: AppState) => (
   id: GP_JSON.ColorSchemeId
): string => {
   const m = predefinedThemes.concat(s.metadata.themes).find(e => e.id == id);
   return m ? m.name : "";
};

/**
 * Rehydrate action generated by redux-persist
 */
export const rehydrate = actionCreator<AppState>(REHYDRATE);
rehydrate.type = REHYDRATE; // no prefix
