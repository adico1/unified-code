#include "machine_internal.h"
#include <ctype.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    const char *name;
    cJSON *row;
} selection;

typedef struct {
    cJSON *state;
    cJSON *arguments;
    selection selected[64];
    size_t selected_count;
} transition_ctx;

static void object_set(cJSON *object, const char *key, cJSON *value) {
    if (cJSON_GetObjectItemCaseSensitive(object, key))
        cJSON_ReplaceItemInObjectCaseSensitive(object, key, value);
    else
        cJSON_AddItemToObject(object, key, value);
}

static cJSON *path_get(cJSON *root, cJSON *path) {
    cJSON *current = root;
    cJSON *key;
    if (!cJSON_IsArray(path)) return NULL;
    for (key = path->child; key != NULL; key = key->next) {
        if (!cJSON_IsObject(current) || !cJSON_IsString(key)) return NULL;
        current = cJSON_GetObjectItemCaseSensitive(current, key->valuestring);
        if (!current) return NULL;
    }
    return current;
}

static int object_size(cJSON *object) {
    int count = 0;
    cJSON *item;
    for (item = object->child; item != NULL; item = item->next) count++;
    return count;
}

static cJSON *selected_row(transition_ctx *ctx, const char *name) {
    size_t index;
    for (index = 0; index < ctx->selected_count; index++)
        if (strcmp(ctx->selected[index].name, name) == 0) return ctx->selected[index].row;
    return NULL;
}

static cJSON *eval_value(cJSON *spec, transition_ctx *ctx) {
    cJSON *node;
    if (cJSON_IsObject(spec) && object_size(spec) == 1) {
        node = cJSON_GetObjectItemCaseSensitive(spec, "$arg");
        if (cJSON_IsString(node)) {
            cJSON *value = cJSON_GetObjectItemCaseSensitive(ctx->arguments, node->valuestring);
            return value ? cJSON_Duplicate(value, 1) : cJSON_CreateNull();
        }
        node = cJSON_GetObjectItemCaseSensitive(spec, "$literal");
        if (node) return cJSON_Duplicate(node, 1);
        node = cJSON_GetObjectItemCaseSensitive(spec, "$state");
        if (cJSON_IsArray(node)) {
            cJSON *value = path_get(ctx->state, node);
            return value ? cJSON_Duplicate(value, 1) : cJSON_CreateNull();
        }
        node = cJSON_GetObjectItemCaseSensitive(spec, "$selected");
        if (cJSON_IsObject(node)) {
            cJSON *name = cJSON_GetObjectItemCaseSensitive(node, "name");
            cJSON *field = cJSON_GetObjectItemCaseSensitive(node, "field");
            cJSON *row = cJSON_IsString(name) ? selected_row(ctx, name->valuestring) : NULL;
            cJSON *value = row && cJSON_IsString(field)
                ? cJSON_GetObjectItemCaseSensitive(row, field->valuestring) : NULL;
            return value ? cJSON_Duplicate(value, 1) : cJSON_CreateNull();
        }
        node = cJSON_GetObjectItemCaseSensitive(spec, "$project");
        if (cJSON_IsObject(node)) {
            cJSON *rows = path_get(ctx->state, cJSON_GetObjectItemCaseSensitive(node, "path"));
            cJSON *fields = cJSON_GetObjectItemCaseSensitive(node, "fields");
            cJSON *projected = cJSON_CreateArray();
            cJSON *row;
            for (row = rows ? rows->child : NULL; row != NULL; row = row->next) {
                cJSON *output = cJSON_CreateObject();
                cJSON *field;
                for (field = fields ? fields->child : NULL; field != NULL; field = field->next) {
                    cJSON *value = cJSON_IsString(field)
                        ? cJSON_GetObjectItemCaseSensitive(row, field->valuestring) : NULL;
                    if (value) cJSON_AddItemToObject(
                        output, field->valuestring, cJSON_Duplicate(value, 1)
                    );
                }
                cJSON_AddItemToArray(projected, output);
            }
            return projected;
        }
    }
    if (cJSON_IsObject(spec)) {
        cJSON *output = cJSON_CreateObject();
        cJSON *item;
        for (item = spec->child; item != NULL; item = item->next)
            cJSON_AddItemToObject(output, item->string, eval_value(item, ctx));
        return output;
    }
    if (cJSON_IsArray(spec)) {
        cJSON *output = cJSON_CreateArray();
        cJSON *item;
        for (item = spec->child; item != NULL; item = item->next)
            cJSON_AddItemToArray(output, eval_value(item, ctx));
        return output;
    }
    return cJSON_Duplicate(spec, 1);
}

static const char *rule_error(cJSON *rule, const char *fallback) {
    cJSON *error = cJSON_GetObjectItemCaseSensitive(rule, "error");
    return cJSON_IsString(error) ? error->valuestring : fallback;
}

static cJSON *parse_argument(cJSON *raw, cJSON *rule, const char **error) {
    cJSON *kind = cJSON_GetObjectItemCaseSensitive(rule, "type");
    const char *type = cJSON_IsString(kind) ? kind->valuestring : "string";
    cJSON *parsed = NULL;
    if (strcmp(type, "string") == 0 && cJSON_IsString(raw)) {
        parsed = cJSON_Duplicate(raw, 1);
    } else if (strcmp(type, "integer") == 0 && cJSON_IsString(raw)) {
        char *end = NULL;
        long value;
        errno = 0;
        value = strtol(raw->valuestring, &end, 10);
        if (end != raw->valuestring) {
            if (errno == 0) {
                if (*end == '\0') parsed = cJSON_CreateNumber((double)value);
            }
        }
    }
    if (!parsed) {
        *error = rule_error(rule, "invalid-argument");
        return NULL;
    }
    {
        cJSON *non_empty = cJSON_GetObjectItemCaseSensitive(rule, "non_empty");
        if (cJSON_IsTrue(non_empty) && cJSON_IsString(parsed)) {
            const unsigned char *cursor = (const unsigned char *)parsed->valuestring;
            while (*cursor && isspace(*cursor)) cursor++;
            if (*cursor == '\0') {
                cJSON_Delete(parsed);
                *error = rule_error(rule, "invalid-argument");
                return NULL;
            }
        }
    }
    {
        cJSON *minimum = cJSON_GetObjectItemCaseSensitive(rule, "minimum");
        if (cJSON_IsNumber(minimum) && cJSON_IsNumber(parsed)
            && parsed->valuedouble < minimum->valuedouble) {
            cJSON_Delete(parsed);
            *error = rule_error(rule, "invalid-argument");
            return NULL;
        }
    }
    return parsed;
}

static int row_matches(cJSON *row, cJSON *where, transition_ctx *ctx) {
    cJSON *clause;
    for (clause = where ? where->child : NULL; clause != NULL; clause = clause->next) {
        cJSON *field = cJSON_GetObjectItemCaseSensitive(clause, "field");
        cJSON *equals = cJSON_GetObjectItemCaseSensitive(clause, "equals");
        cJSON *actual = cJSON_IsString(field)
            ? cJSON_GetObjectItemCaseSensitive(row, field->valuestring) : NULL;
        cJSON *expected = eval_value(equals, ctx);
        int same = actual && cJSON_Compare(actual, expected, 1);
        cJSON_Delete(expected);
        if (!same) return 0;
    }
    return 1;
}

static const char *apply_guard(cJSON *rule, transition_ctx *ctx) {
    cJSON *kind = cJSON_GetObjectItemCaseSensitive(rule, "kind");
    cJSON *rows = path_get(ctx->state, cJSON_GetObjectItemCaseSensitive(rule, "path"));
    cJSON *where = cJSON_GetObjectItemCaseSensitive(rule, "where");
    cJSON *row;
    cJSON *match = NULL;
    for (row = rows ? rows->child : NULL; row != NULL; row = row->next) {
        if (row_matches(row, where, ctx)) {
            match = row;
            break;
        }
    }
    if (cJSON_IsString(kind) && strcmp(kind->valuestring, "unique") == 0)
        return match ? rule_error(rule, "invalid-guard") : NULL;
    if (cJSON_IsString(kind) && strcmp(kind->valuestring, "require") == 0) {
        cJSON *alias = cJSON_GetObjectItemCaseSensitive(rule, "as");
        if (!match) return rule_error(rule, "invalid-guard");
        if (!cJSON_IsString(alias) || ctx->selected_count >= 64) return "invalid-guard";
        ctx->selected[ctx->selected_count].name = alias->valuestring;
        ctx->selected[ctx->selected_count].row = match;
        ctx->selected_count++;
        return NULL;
    }
    return "invalid-guard";
}

static int apply_action(cJSON *rule, transition_ctx *ctx) {
    cJSON *kind = cJSON_GetObjectItemCaseSensitive(rule, "kind");
    if (cJSON_IsString(kind) && strcmp(kind->valuestring, "append") == 0) {
        cJSON *rows = path_get(ctx->state, cJSON_GetObjectItemCaseSensitive(rule, "path"));
        cJSON_AddItemToArray(rows, eval_value(cJSON_GetObjectItemCaseSensitive(rule, "value"), ctx));
        return 1;
    }
    if (cJSON_IsString(kind)
        && (strcmp(kind->valuestring, "set") == 0
            || strcmp(kind->valuestring, "increment") == 0)) {
        cJSON *target_name = cJSON_GetObjectItemCaseSensitive(rule, "target");
        cJSON *target = cJSON_IsString(target_name)
            ? selected_row(ctx, target_name->valuestring) : NULL;
        cJSON *values = cJSON_GetObjectItemCaseSensitive(rule, "values");
        cJSON *field;
        for (field = values ? values->child : NULL; field != NULL; field = field->next) {
            cJSON *value = eval_value(field, ctx);
            if (strcmp(kind->valuestring, "increment") == 0) {
                cJSON *current = cJSON_GetObjectItemCaseSensitive(target, field->string);
                double sum = (cJSON_IsNumber(current) ? current->valuedouble : 0.0)
                    + (cJSON_IsNumber(value) ? value->valuedouble : 0.0);
                cJSON_Delete(value);
                value = cJSON_CreateNumber(sum);
            }
            object_set(target, field->string, value);
        }
        return 1;
    }
    return 0;
}

static cJSON *envelope(cJSON *state, cJSON *result, int changed, const char *error) {
    cJSON *output = cJSON_CreateObject();
    cJSON_AddItemToObject(output, "resource_state", cJSON_Duplicate(state, 1));
    cJSON_AddItemToObject(output, "result", result ? result : cJSON_CreateNull());
    cJSON_AddBoolToObject(output, "state_changed", changed);
    if (error) cJSON_AddStringToObject(output, "error", error);
    else cJSON_AddNullToObject(output, "error");
    return output;
}

int uem_stateful_transition(uem_machine *m) {
    cJSON *config = cJSON_GetObjectItemCaseSensitive(m->image, "stateful");
    cJSON *commands = config ? cJSON_GetObjectItemCaseSensitive(config, "commands") : NULL;
    cJSON *command_name = m->host
        ? cJSON_GetObjectItemCaseSensitive(m->host, "command") : NULL;
    cJSON *raw_arguments = m->host
        ? cJSON_GetObjectItemCaseSensitive(m->host, "arguments") : NULL;
    cJSON *original = m->host
        ? cJSON_GetObjectItemCaseSensitive(m->host, "resource_state") : NULL;
    cJSON *command = cJSON_IsString(command_name) && cJSON_IsObject(commands)
        ? cJSON_GetObjectItemCaseSensitive(commands, command_name->valuestring) : NULL;
    cJSON *state = original ? cJSON_Duplicate(original, 1) : cJSON_CreateObject();
    cJSON *arguments = cJSON_CreateObject();
    cJSON *rules = command ? cJSON_GetObjectItemCaseSensitive(command, "arguments") : NULL;
    const char *error = NULL;
    transition_ctx ctx;
    cJSON *rule;
    int raw_count = cJSON_IsArray(raw_arguments) ? cJSON_GetArraySize(raw_arguments) : 0;
    int rule_count = cJSON_IsArray(rules) ? cJSON_GetArraySize(rules) : 0;
    memset(&ctx, 0, sizeof ctx);
    ctx.state = state;
    ctx.arguments = arguments;
    if (!command) error = "unknown-command";
    else if (raw_count != rule_count) error = "invalid-arity";
    if (!error) {
        int index = 0;
        for (rule = rules ? rules->child : NULL; rule != NULL; rule = rule->next, index++) {
            cJSON *name = cJSON_GetObjectItemCaseSensitive(rule, "name");
            cJSON *parsed = parse_argument(cJSON_GetArrayItem(raw_arguments, index), rule, &error);
            if (error) break;
            cJSON_AddItemToObject(arguments, name->valuestring, parsed);
        }
    }
    if (!error) {
        cJSON *guards = cJSON_GetObjectItemCaseSensitive(command, "guards");
        for (rule = guards ? guards->child : NULL; rule != NULL; rule = rule->next) {
            error = apply_guard(rule, &ctx);
            if (error) break;
        }
    }
    if (error) {
        cJSON *stats = envelope(original ? original : state, NULL, 0, error);
        object_set(m->store, "stats", stats);
        object_set(m->store, "error", cJSON_CreateString(error));
        cJSON_Delete(state);
        cJSON_Delete(arguments);
        uem_set_state(m, "invalid");
        uem_ev_append(m, "part:state_transition");
        {
            char mark[192];
            snprintf(mark, sizeof mark, "state_transition:error:%s", error);
            return uem_ev_append(m, mark);
        }
    }
    {
        cJSON *actions = cJSON_GetObjectItemCaseSensitive(command, "actions");
        cJSON *result_spec = cJSON_GetObjectItemCaseSensitive(command, "result");
        int changed = 0;
        for (rule = actions ? actions->child : NULL; rule != NULL; rule = rule->next)
            changed = apply_action(rule, &ctx) || changed;
        object_set(m->store, "stats", envelope(state, eval_value(result_spec, &ctx), changed, NULL));
    }
    cJSON_Delete(state);
    cJSON_Delete(arguments);
    uem_ev_append(m, "part:state_transition");
    return uem_ev_append(m, "state_transition:ok");
}
