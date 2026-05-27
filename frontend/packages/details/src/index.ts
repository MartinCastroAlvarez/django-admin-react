// @dar/details — the read/display surface for a single object.
//
// Today this is the read-only field-value renderer (`FieldValueView`),
// shared by the list, the detail page, and `@dar/form` (readonly fields).
// The detail-page orchestration itself still lives in `@dar/web` and is
// slated to move here (issue #303).

export { FieldValueView } from './FieldValueView';
