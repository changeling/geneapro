import { Source, SourceSet } from "../Store/Source";
import { AssertionList } from "../Store/Assertion";
import {
   AssertionEntities,
   AssertionEntitiesJSON,
   assertionFromJSON,
   setAssertionEntities
} from "../Server/Person";
import * as JSON from "../Server/JSON";

interface JSONResult extends AssertionEntitiesJSON {
   source: JSON.Source;
   higher_sources: number[];
   asserts: JSON.Assertion[];
   repr: JSON.SourceRepr[];
   parts: JSON.CitationPart[];
}

export interface FetchSourceDetailsResult extends AssertionEntities {
   source: Source;
}

export function sourceFromJSON(s: JSON.Source) {
   const result: Source = {
      id: s.id,
      title: s.title,
      abbrev: s.abbrev,
      biblio: s.biblio,
      comments: s.comments,
      higherSourceId: s.higher_source_id,
      medium: s.medium,
      jurisdictionPlace: s.jurisdiction_place,
      lastChange: new Date(s.last_change),
      subjectDate: s.subject_date,
      subjectPlace: s.subject_place,
      parts: {}
   };
   return result;
}

export function* fetchSourceDetailsFromServer(id: number) {
   const resp: Response = yield window.fetch("/data/sources/" + id);
   if (resp.status !== 200) {
      throw new Error("Server returned an error");
   }
   const data: JSONResult = yield resp.json();

   let r: FetchSourceDetailsResult = {
      source: {
         ...sourceFromJSON(data.source),
         asserts: new AssertionList(
            data.asserts.map(a => assertionFromJSON(a))),
         medias: data.repr,
         parts: data.parts ? data.parts.reduce(
            (val, part) => ({...val, [part.name]: part}), {})
            : {},
      },
      events: {},
      persons: {},
      places: {},
      sources: {},
   };

   setAssertionEntities(data, r);
   return r;
}

export function fetchSourcesFromServer(
   p: {
      offset?: number;
      limit?: number;
      filter?: string;
      ids?: number[];
   }
): Promise<Source[]> {
   const url =
      '/data/sources/list?' +
      (p.filter ? `&filter=${encodeURI(p.filter)}` : '') +
      (p.offset ? `&offset=${p.offset}` : '') +
      (p.limit ? `&limit=${p.limit}` : '') +
      (p.ids ? `&ids=${p.ids.join(',')}` : '');
   return window.fetch(url)
      .then((resp: Response) => resp.json());
}

/**
 * Fetch the total number of sources matching the filter
 */
export const fetchSourcesCount = (p: {filter: string}): Promise<number> =>
   fetch(`/data/sources/count?filter=${encodeURI(p.filter)}`)
   .then((r: Response) => r.json());

