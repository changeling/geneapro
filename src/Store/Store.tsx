import * as Redux from 'redux';
import createSagaMiddleware from 'redux-saga';
import { persistStore, autoRehydrate } from 'redux-persist';
import { AppState, GPStore } from '../Store/State';
import { fanchartReducer } from '../Store/Fanchart';
import { pedigreeReducer } from '../Store/PedigreeReducer';
import { personsReducer, historyReducer, eventsReducer,
         sourcesReducer } from '../Store/Reducers';
import { rootSaga } from '../Store/Sagas';
import { csrfReducer } from '../Store/Csrf';

export const rootReducer = Redux.combineReducers<AppState>({
   pedigree: pedigreeReducer,
   fanchart: fanchartReducer,
   persons: personsReducer,
   history: historyReducer,
   events: eventsReducer,
   sources: sourcesReducer,
   csrf: csrfReducer,
});

// Use generators as reducers
const sagaMiddleware = createSagaMiddleware();

const middlewares: Redux.Middleware[] = [
   sagaMiddleware,
];

if (process.env.NODE_ENV === `development`) {
   // Log actions to the console
   const { createLogger } = require('redux-logger');
   middlewares.push(
      createLogger({collapsed: true,
                    duration: true,
                    diff: true}));   // log actions in the console
}

export const store: GPStore = Redux.createStore(
   rootReducer /* reducer */,
   Redux.compose(  /* enhancer */
      Redux.applyMiddleware(...middlewares) as Redux.StoreEnhancer<AppState>,
      autoRehydrate<AppState>({log: false}) // load from persistent storage
   )
);

sagaMiddleware.run(rootSaga);

/**
 * Make the store persistent. This will be called from the main component's
 * componentDidMount, so that we can set a 'loading...' state while we restore
 * and thus avoid displaying the default settings.
 */
export function setPersist(whenDone: () => void) {
   persistStore(
      store,
      {
         // ??? Should not save pedigree.loading
         whitelist: ['pedigree', 'fanchart', 'history'],
      },
      whenDone
   );
}
