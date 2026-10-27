library(shiny)
library(ggplot2)
library(DT)

find_root <- function() {
  env <- Sys.getenv("TRIVENI_ROOT", "")
  if (nzchar(env)) return(normalizePath(env, winslash = "/", mustWork = TRUE))
  x <- normalizePath(getwd(), winslash = "/", mustWork = TRUE)
  repeat {
    if (file.exists(file.path(x, "module_references/triveni-clin/SDY4"))) return(x)
    parent <- dirname(x)
    if (parent == x) stop("Could not find module_references/triveni-clin/SDY4")
    x <- parent
  }
}
root <- find_root()
tab_dir <- file.path(root, "module_references/triveni-clin/SDY4/extracted/SDY4-DR65_Tab/Tab")
zip_file <- file.path(root, "module_references/triveni-clin/SDY4/SDY4-DR65_Tab.zip")

if (!file.exists(file.path(tab_dir, "lab_test.txt")) && file.exists(zip_file)) {
  unzip(zip_file, exdir = file.path(root, "module_references/triveni-clin/SDY4/extracted"))
}
stopifnot(file.exists(file.path(tab_dir, "lab_test.txt")))

read_tab <- function(name) read.delim(file.path(tab_dir, paste0(name, ".txt")), sep = "\t", stringsAsFactors = FALSE, check.names = FALSE)

arm <- read_tab("arm_or_cohort")[, c("ARM_ACCESSION", "NAME")]
a2s <- read_tab("arm_2_subject")
subj <- read_tab("subject")[, c("SUBJECT_ACCESSION", "GENDER", "RACE", "ETHNICITY")]
bios <- read_tab("biosample")[, c("BIOSAMPLE_ACCESSION", "SUBJECT_ACCESSION", "PLANNED_VISIT_ACCESSION", "TYPE")]
lab <- read_tab("lab_test")

meta <- merge(merge(a2s, arm, by = "ARM_ACCESSION", all.x = TRUE), subj, by = "SUBJECT_ACCESSION", all.x = TRUE)
meta$Group <- ifelse(meta$NAME == "Healthy controls", "Healthy controls", "Atopic dermatitis arms")
meta$Age <- suppressWarnings(as.numeric(meta$MAX_SUBJECT_AGE_IN_YEARS))

lab <- merge(lab, bios, by = "BIOSAMPLE_ACCESSION", all.x = TRUE)
lab$Value <- suppressWarnings(as.numeric(lab$RESULT_VALUE_PREFERRED))
d <- merge(lab[!is.na(lab$Value) & lab$NAME_REPORTED != "", ], meta, by = "SUBJECT_ACCESSION", all.x = TRUE)
measures <- sort(unique(d$NAME_REPORTED))

default_measures <- intersect(c("Eosinophils", "Eosinophils percentage", "Leukocytes", "Lymphocytes", "Neutrophils", "Monocytes", "Total IgE"), measures)

system_prompt <- paste(
  "You are Triveni's interactive clinical EDA assistant.",
  "Answer only from the SDY4 summaries provided in the user message.",
  "Be concise, exploratory, and cautious: no causal claims; mention missingness/sample size when relevant.",
  "Suggest one next plot or table the reviewer should inspect.",
  sep = "\n"
)

make_chat_client <- function() {
  if (!requireNamespace("ellmer", quietly = TRUE)) return(NULL)
  provider <- tolower(Sys.getenv("TRIVENI_LLM_PROVIDER", "openai"))
  tryCatch({
    if (provider == "ollama") {
      ellmer::chat_ollama(system_prompt = system_prompt, model = Sys.getenv("OLLAMA_MODEL", "llama3.1"))
    } else {
      ellmer::chat_openai(system_prompt = system_prompt, model = Sys.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    }
  }, error = function(e) NULL)
}

subject_values <- function(measure_names) {
  x <- d[d$NAME_REPORTED %in% measure_names, ]
  aggregate(Value ~ SUBJECT_ACCESSION + NAME_REPORTED + Group + NAME + GENDER + RACE + ETHNICITY + Age, x, mean, na.rm = TRUE)
}

screen_table <- function() {
  out <- do.call(rbind, lapply(measures, function(m) {
    x <- subject_values(m)
    ad <- x$Value[x$Group == "Atopic dermatitis arms"]
    hc <- x$Value[x$Group == "Healthy controls"]
    p <- if (length(ad) > 1 && length(hc) > 1) t.test(ad, hc)$p.value else NA_real_
    data.frame(
      measure = m, ad_n = length(ad), healthy_n = length(hc),
      ad_mean = mean(ad), healthy_mean = mean(hc), diff = mean(ad) - mean(hc),
      p_value = p, stringsAsFactors = FALSE
    )
  }))
  out$fdr <- p.adjust(out$p_value, "BH")
  out$abs_diff <- abs(out$diff)
  out <- out[!is.na(out$diff), ]
  out[order(out$fdr, -out$abs_diff), c("measure", "ad_n", "healthy_n", "ad_mean", "healthy_mean", "diff", "p_value", "fdr")]
}

ui <- fluidPage(
  titlePanel("Triveni EDA · ImmPort SDY4 clinical labs"),
  sidebarLayout(
    sidebarPanel(
      selectizeInput("measure", "Lab measure(s)", choices = measures, selected = default_measures[1:min(3, length(default_measures))], multiple = TRUE),
      checkboxInput("split_arm", "Split AD into original SDY4 arms", FALSE),
      selectInput("plot", "Plot", c("Box + jitter" = "box", "Violin + jitter" = "violin", "Mean bar" = "bar")),
      helpText("Exploratory only: repeated biosamples are averaged per subject/measure; no covariate model here.")
    ),
    mainPanel(
      tabsetPanel(
        tabPanel("Plot", plotOutput("plot", height = 340)),
        tabPanel("Ask", uiOutput("chat_ui")),
        tabPanel("Screen", DTOutput("screen")),
        tabPanel("Data", DTOutput("data"))
      )
    )
  )
)

server <- function(input, output, session) {
  client <- make_chat_client()

  selected <- reactive({
    req(input$measure)
    x <- subject_values(input$measure)
    x$PlotGroup <- if (isTRUE(input$split_arm)) x$NAME else x$Group
    x
  })

  output$plot <- renderPlot({
    x <- selected()
    p <- ggplot(x, aes(PlotGroup, Value, fill = PlotGroup)) + facet_wrap(~ NAME_REPORTED, scales = "free_y") + theme_bw(base_size = 10) + theme(axis.text.x = element_text(angle = 30, hjust = 1, size = 8), legend.position = "none", strip.text = element_text(size = 8)) + labs(x = NULL, y = "Subject-level mean value")
    if (input$plot == "violin") p + geom_violin(trim = FALSE, alpha = 0.5) + geom_jitter(width = 0.15, alpha = 0.7)
    else if (input$plot == "bar") p + stat_summary(fun = mean, geom = "col", alpha = 0.7) + stat_summary(fun.data = mean_se, geom = "errorbar", width = 0.2)
    else p + geom_boxplot(outlier.shape = NA, alpha = 0.5) + geom_jitter(width = 0.15, alpha = 0.7)
  })

  output$chat_ui <- renderUI({
    if (requireNamespace("shinychat", quietly = TRUE)) {
      shinychat::chat_ui(
        "chat",
        height = "360px",
        fill = FALSE,
        allow_attachments = FALSE,
        show_history = FALSE,
        greeting = shinychat::chat_greeting("Ask about the selected SDY4 labs, e.g. *Which markers are most elevated and what should I plot next?*")
      )
    } else {
      tagList(
        p("Install shinychat and ellmer for conversational EDA:"),
        code("install.packages(c('shinychat', 'ellmer'))")
      )
    }
  })

  observeEvent(input$chat_user_input, {
    req(requireNamespace("shinychat", quietly = TRUE))
    question <- input$chat_user_input
    context <- paste(
      "Selected measures:", paste(input$measure, collapse = ", "),
      "\nCurrent subject-level data preview:\n", paste(capture.output(print(utils::head(selected(), 20))), collapse = "\n"),
      "\nTop SDY4 screen rows:\n", paste(capture.output(print(utils::head(screen_table(), 12))), collapse = "\n"),
      "\nReviewer question:", question
    )
    answer <- if (is.null(client)) {
      paste(
        "LLM client is not configured. Set OPENAI_API_KEY for OpenAI or TRIVENI_LLM_PROVIDER=ollama with OLLAMA_MODEL for a local model.",
        "\n\nMeanwhile, inspect the Screen tab: it ranks measures by BH-FDR and effect size; the Plot tab shows subject-level distributions."
      )
    } else {
      tryCatch(client$chat(context), error = function(e) paste("LLM call failed:", e$message))
    }
    shinychat::chat_append("chat", answer)
  })

  output$screen <- renderDT(datatable(screen_table(), options = list(pageLength = 12, scrollX = TRUE), rownames = FALSE))
  output$data <- renderDT(datatable(selected(), options = list(pageLength = 12, scrollX = TRUE), rownames = FALSE))
}

shinyApp(ui, server)
